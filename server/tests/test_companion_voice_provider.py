from __future__ import annotations

import base64
import json
from urllib.request import Request

import pytest

from app.core.companion_experience import VoiceBoundary
from app.core.companion_voice_provider import (
    HttpJsonVoiceProvider,
    HttpVoiceProviderConfig,
    configured_voice_boundary,
    normalize_voice_provider_url,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object], *, status: int = 200) -> None:
        self.status = status
        self.raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit: int = -1) -> bytes:
        return self.raw if limit < 0 else self.raw[:limit]


def test_provider_url_requires_https_except_explicit_loopback() -> None:
    assert normalize_voice_provider_url("https://voice.example.com/") == "https://voice.example.com"
    assert normalize_voice_provider_url("http://127.0.0.1:9900/") == "http://127.0.0.1:9900"
    assert normalize_voice_provider_url("http://localhost:9900") == "http://localhost:9900"
    with pytest.raises(ValueError, match="VOICE_PROVIDER_HTTPS_REQUIRED"):
        normalize_voice_provider_url("http://voice.example.com")
    with pytest.raises(ValueError, match="VOICE_PROVIDER_URL_INVALID"):
        normalize_voice_provider_url("https://user:secret@voice.example.com")
    with pytest.raises(ValueError, match="VOICE_PROVIDER_URL_INVALID"):
        normalize_voice_provider_url("file:///tmp/provider")


def test_http_voice_provider_sends_bounded_vendor_neutral_contract_without_url_credentials() -> None:
    calls: list[tuple[Request, float]] = []

    def opener(request: Request, *, timeout: float):
        calls.append((request, timeout))
        if request.full_url.endswith("/v1/stt"):
            return FakeResponse({"transcript": "acknowledge"})
        if request.full_url.endswith("/v1/tts"):
            return FakeResponse({
                "audio_b64": base64.b64encode(b"RIFF-provider-wav").decode("ascii"),
                "content_type": "audio/wav",
            })
        raise AssertionError(request.full_url)

    provider = HttpJsonVoiceProvider(
        HttpVoiceProviderConfig(
            base_url="https://voice.example.com",
            bearer_token="provider-token-value",
            timeout_seconds=3.5,
        ),
        opener=opener,
    )

    assert provider.transcribe(b"opus-audio", locale="en") == "acknowledge"
    assert provider.synthesize("Acknowledged.", locale="en") == b"RIFF-provider-wav"
    assert [request.full_url for request, _ in calls] == [
        "https://voice.example.com/v1/stt",
        "https://voice.example.com/v1/tts",
    ]
    assert all(timeout == 3.5 for _, timeout in calls)
    assert all("provider-token-value" not in request.full_url for request, _ in calls)
    assert all(request.get_header("Authorization") == "Bearer provider-token-value" for request, _ in calls)

    stt_body = json.loads(calls[0][0].data.decode("utf-8"))
    assert base64.b64decode(stt_body["audio_b64"]) == b"opus-audio"
    assert stt_body["content_type"] == "audio/webm;codecs=opus"
    assert stt_body["locale"] == "en"


def test_provider_rejects_invalid_or_unbounded_responses() -> None:
    def invalid_transcript(_request: Request, *, timeout: float):
        return FakeResponse({"transcript": ""})

    provider = HttpJsonVoiceProvider(
        HttpVoiceProviderConfig(base_url="https://voice.example.com"),
        opener=invalid_transcript,
    )
    with pytest.raises(RuntimeError, match="VOICE_PROVIDER_TRANSCRIPT_INVALID"):
        provider.transcribe(b"audio", locale="en")

    def invalid_audio(_request: Request, *, timeout: float):
        return FakeResponse({"audio_b64": "not-base64", "content_type": "audio/wav"})

    provider = HttpJsonVoiceProvider(
        HttpVoiceProviderConfig(base_url="https://voice.example.com"),
        opener=invalid_audio,
    )
    with pytest.raises(RuntimeError, match="VOICE_PROVIDER_AUDIO_INVALID"):
        provider.synthesize("Status", locale="en")


def test_configured_boundary_is_fail_closed_without_environment_and_configurable_without_vendor_sdk(monkeypatch) -> None:
    monkeypatch.delenv("SENTINEL_VOICE_PROVIDER_URL", raising=False)
    monkeypatch.delenv("SENTINEL_VOICE_PROVIDER_TOKEN", raising=False)
    boundary = configured_voice_boundary()
    assert isinstance(boundary, VoiceBoundary)
    assert boundary.stt is None
    assert boundary.tts is None

    monkeypatch.setenv("SENTINEL_VOICE_PROVIDER_URL", "http://voice.example.com")
    with pytest.raises(RuntimeError, match="VOICE_PROVIDER_CONFIGURATION_INVALID"):
        configured_voice_boundary()
