from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from threading import Lock
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

_EMAIL = re.compile(r"^[^\s@]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,63}$")
_SUBJECT = re.compile(r"^[^\r\n]{1,160}$")
_MAX_TEXT_BYTES = 32_768
_MAX_RESPONSE_BYTES = 65_536


class EmailProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailMessage:
    to_address: str
    subject: str
    text: str

    def __post_init__(self) -> None:
        if not _EMAIL.fullmatch(self.to_address):
            raise ValueError("EMAIL_RECIPIENT_INVALID")
        if not _SUBJECT.fullmatch(self.subject):
            raise ValueError("EMAIL_SUBJECT_INVALID")
        encoded = self.text.encode("utf-8")
        if not encoded or len(encoded) > _MAX_TEXT_BYTES:
            raise ValueError("EMAIL_TEXT_INVALID")


class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> str: ...


class DisabledEmailTransport:
    def send(self, message: EmailMessage) -> str:
        del message
        raise EmailProviderUnavailable("EMAIL_PROVIDER_UNAVAILABLE")


class TestEmailTransport:
    """Deterministic no-network transport used by tests and local integration."""

    __test__ = False  # Provider fixture, not a pytest test class.

    def __init__(self, *, max_messages: int = 32) -> None:
        if max_messages <= 0 or max_messages > 256:
            raise ValueError("EMAIL_TEST_BUFFER_INVALID")
        self._max_messages = max_messages
        self._messages: list[EmailMessage] = []
        self._lock = Lock()

    def send(self, message: EmailMessage) -> str:
        with self._lock:
            if len(self._messages) >= self._max_messages:
                self._messages.pop(0)
            self._messages.append(message)
            index = len(self._messages)
        return f"test-email-{index}"

    def snapshot(self) -> tuple[EmailMessage, ...]:
        with self._lock:
            return tuple(self._messages)


@dataclass(frozen=True)
class ResendConfig:
    api_key: str = field(repr=False)
    from_address: str
    endpoint: str = "https://api.resend.com/emails"

    def __post_init__(self) -> None:
        if not self.api_key.startswith("re_") or len(self.api_key) < 12:
            raise ValueError("RESEND_API_KEY_INVALID")
        if not _EMAIL.fullmatch(self.from_address):
            raise ValueError("RESEND_FROM_ADDRESS_INVALID")
        parts = urlsplit(self.endpoint)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("RESEND_ENDPOINT_INVALID")


class ResendEmailTransport:
    """Fail-closed Resend adapter; credentials remain environment-injected."""

    def __init__(self, config: ResendConfig, *, timeout_seconds: float = 8.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 20:
            raise ValueError("RESEND_TIMEOUT_INVALID")
        self._config = config
        self._timeout_seconds = timeout_seconds

    def send(self, message: EmailMessage) -> str:
        payload = json.dumps(
            {
                "from": self._config.from_address,
                "to": [message.to_address],
                "subject": message.subject,
                "text": message.text,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            self._config.endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "sentinel-core/resend-adapter",
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise EmailProviderUnavailable(f"RESEND_HTTP_{exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise EmailProviderUnavailable("RESEND_UNAVAILABLE") from exc
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise EmailProviderUnavailable("RESEND_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EmailProviderUnavailable("RESEND_RESPONSE_INVALID") from exc
        message_id = result.get("id") if isinstance(result, dict) else None
        if not isinstance(message_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{6,256}", message_id):
            raise EmailProviderUnavailable("RESEND_RESPONSE_INVALID")
        return message_id


def configured_email_transport() -> EmailTransport:
    """Return a provider only when staging Resend configuration is complete."""

    if not _strict_env_bool("SENTINEL_RESEND_ENABLED", default=False):
        return DisabledEmailTransport()
    environment = os.getenv("SENTINEL_ENV", "development").strip().lower()
    if environment != "staging":
        raise RuntimeError("RESEND_STAGING_ONLY")
    api_key = os.getenv("SENTINEL_RESEND_API_KEY", "")
    from_address = os.getenv("SENTINEL_RESEND_FROM_ADDRESS", "")
    if not api_key or not from_address:
        raise RuntimeError("RESEND_NOT_CONFIGURED")
    try:
        return ResendEmailTransport(ResendConfig(api_key=api_key, from_address=from_address))
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc


def _strict_env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RuntimeError(f"{name}_INVALID")
