from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import os
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .companion_experience import VoiceBoundary

_STT_PATH = "/v1/stt"
_TTS_PATH = "/v1/tts"
_MAX_PROVIDER_RESPONSE_BYTES = 2_800_000
_MAX_TRANSCRIPT_CHARS = 2_000
_MAX_AUDIO_BYTES = 2_000_000


def _is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def normalize_voice_provider_url(value: str) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("VOICE_PROVIDER_URL_INVALID")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("VOICE_PROVIDER_URL_INVALID")
    if parsed.scheme != "https" and not _is_loopback_host(parsed.hostname):
        raise ValueError("VOICE_PROVIDER_HTTPS_REQUIRED")
    path = parsed.path.rstrip("/")
    return parsed._replace(path=path, params="", query="", fragment="").geturl().rstrip("/")


@dataclass(frozen=True, slots=True)
class HttpVoiceProviderConfig:
    base_url: str
    bearer_token: str | None = None
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", normalize_voice_provider_url(self.base_url))
        if self.bearer_token is not None and (
            not self.bearer_token
            or len(self.bearer_token) > 4096
            or "\r" in self.bearer_token
            or "\n" in self.bearer_token
        ):
            raise ValueError("VOICE_PROVIDER_TOKEN_INVALID")
        if not 0.1 <= self.timeout_seconds <= 30.0:
            raise ValueError("VOICE_PROVIDER_TIMEOUT_INVALID")


class HttpJsonVoiceProvider:
    """Provider-neutral JSON-over-HTTP STT/TTS adapter.

    The provider contract is intentionally narrow and vendor-neutral:
    POST /v1/stt -> {"transcript": "..."}
    POST /v1/tts -> {"audio_b64": "...", "content_type": "audio/wav"}

    Production credentials are injected from process environment and are never
    returned through application APIs or written to audit records.
    """

    def __init__(
        self,
        config: HttpVoiceProviderConfig,
        *,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.config = config
        self._opener = opener

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.config.bearer_token:
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        request = Request(f"{self.config.base_url}{path}", data=body, headers=headers, method="POST")
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                raw = response.read(_MAX_PROVIDER_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise RuntimeError("VOICE_PROVIDER_REQUEST_FAILED") from exc
        if status < 200 or status >= 300:
            raise RuntimeError("VOICE_PROVIDER_REQUEST_FAILED")
        if len(raw) > _MAX_PROVIDER_RESPONSE_BYTES:
            raise RuntimeError("VOICE_PROVIDER_RESPONSE_TOO_LARGE")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("VOICE_PROVIDER_RESPONSE_INVALID") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError("VOICE_PROVIDER_RESPONSE_INVALID")
        return decoded

    def transcribe(self, audio: bytes, *, locale: str) -> str:
        payload = self._post_json(
            _STT_PATH,
            {
                "audio_b64": base64.b64encode(audio).decode("ascii"),
                "content_type": "audio/webm;codecs=opus",
                "locale": locale,
            },
        )
        transcript = payload.get("transcript")
        if not isinstance(transcript, str):
            raise RuntimeError("VOICE_PROVIDER_TRANSCRIPT_INVALID")
        transcript = transcript.strip()
        if not transcript or len(transcript) > _MAX_TRANSCRIPT_CHARS:
            raise RuntimeError("VOICE_PROVIDER_TRANSCRIPT_INVALID")
        return transcript

    def synthesize(self, text: str, *, locale: str) -> bytes:
        payload = self._post_json(_TTS_PATH, {"text": text, "locale": locale, "content_type": "audio/wav"})
        if payload.get("content_type") != "audio/wav":
            raise RuntimeError("VOICE_PROVIDER_AUDIO_INVALID")
        encoded = payload.get("audio_b64")
        if not isinstance(encoded, str) or not encoded:
            raise RuntimeError("VOICE_PROVIDER_AUDIO_INVALID")
        try:
            audio = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise RuntimeError("VOICE_PROVIDER_AUDIO_INVALID") from exc
        if not audio or len(audio) > _MAX_AUDIO_BYTES:
            raise RuntimeError("VOICE_PROVIDER_AUDIO_INVALID")
        return audio


def configured_voice_boundary() -> VoiceBoundary:
    endpoint = os.getenv("SENTINEL_VOICE_PROVIDER_URL", "").strip()
    if not endpoint:
        return VoiceBoundary()
    token = os.getenv("SENTINEL_VOICE_PROVIDER_TOKEN") or None
    raw_timeout = os.getenv("SENTINEL_VOICE_PROVIDER_TIMEOUT_SECONDS", "10")
    try:
        timeout = float(raw_timeout)
        provider = HttpJsonVoiceProvider(
            HttpVoiceProviderConfig(base_url=endpoint, bearer_token=token, timeout_seconds=timeout)
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("VOICE_PROVIDER_CONFIGURATION_INVALID") from exc
    return VoiceBoundary(stt=provider, tts=provider)
