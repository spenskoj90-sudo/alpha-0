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
    allowed_recipients: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.startswith("re_") or len(self.api_key) < 12:
            raise ValueError("RESEND_API_KEY_INVALID")
        if not _EMAIL.fullmatch(self.from_address):
            raise ValueError("RESEND_FROM_ADDRESS_INVALID")
        if len(self.allowed_recipients) > 32 or any(
            not _EMAIL.fullmatch(recipient) for recipient in self.allowed_recipients
        ):
            raise ValueError("RESEND_ALLOWED_RECIPIENTS_INVALID")
        if self.from_address.rsplit("@", 1)[1].lower() == "resend.dev" and not self.allowed_recipients:
            raise ValueError("RESEND_SANDBOX_RECIPIENTS_REQUIRED")
        parts = urlsplit(self.endpoint)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("RESEND_ENDPOINT_INVALID")


@dataclass(frozen=True)
class BrevoConfig:
    api_key: str = field(repr=False)
    from_address: str
    from_name: str = "SENTINEL"
    endpoint: str = "https://api.brevo.com/v3/smtp/email"

    def __post_init__(self) -> None:
        if not self.api_key.startswith("xkeysib-") or len(self.api_key) < 20 or len(self.api_key) > 512:
            raise ValueError("BREVO_API_KEY_INVALID")
        if not _EMAIL.fullmatch(self.from_address):
            raise ValueError("BREVO_FROM_ADDRESS_INVALID")
        if not self.from_name or len(self.from_name.encode("utf-8")) > 120 or "\r" in self.from_name or "\n" in self.from_name:
            raise ValueError("BREVO_FROM_NAME_INVALID")
        parts = urlsplit(self.endpoint)
        if (
            parts.scheme != "https"
            or parts.hostname != "api.brevo.com"
            or parts.path != "/v3/smtp/email"
            or parts.query
            or parts.fragment
            or parts.username
            or parts.password
        ):
            raise ValueError("BREVO_ENDPOINT_INVALID")


class BrevoEmailTransport:
    """Fail-closed Brevo HTTPS adapter for Render-free-compatible staging delivery."""

    def __init__(self, config: BrevoConfig, *, timeout_seconds: float = 8.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 20:
            raise ValueError("BREVO_TIMEOUT_INVALID")
        self._config = config
        self._timeout_seconds = timeout_seconds

    def send(self, message: EmailMessage) -> str:
        payload = json.dumps(
            {
                "sender": {
                    "email": self._config.from_address,
                    "name": self._config.from_name,
                },
                "to": [{"email": message.to_address}],
                "subject": message.subject,
                "textContent": message.text,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            self._config.endpoint,
            data=payload,
            method="POST",
            headers={
                "api-key": self._config.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "sentinel-core/brevo-adapter",
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise EmailProviderUnavailable(f"BREVO_HTTP_{exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise EmailProviderUnavailable("BREVO_UNAVAILABLE") from exc
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise EmailProviderUnavailable("BREVO_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EmailProviderUnavailable("BREVO_RESPONSE_INVALID") from exc
        message_id = result.get("messageId") if isinstance(result, dict) else None
        if (
            not isinstance(message_id, str)
            or len(message_id) < 6
            or len(message_id) > 512
            or "\r" in message_id
            or "\n" in message_id
        ):
            raise EmailProviderUnavailable("BREVO_RESPONSE_INVALID")
        return message_id


class ResendEmailTransport:
    """Fail-closed Resend adapter; credentials remain environment-injected."""

    def __init__(self, config: ResendConfig, *, timeout_seconds: float = 8.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 20:
            raise ValueError("RESEND_TIMEOUT_INVALID")
        self._config = config
        self._timeout_seconds = timeout_seconds

    def send(self, message: EmailMessage) -> str:
        if self._config.allowed_recipients and message.to_address.lower() not in {
            recipient.lower() for recipient in self._config.allowed_recipients
        }:
            raise EmailProviderUnavailable("RESEND_RECIPIENT_NOT_ALLOWED")
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
    """Return exactly one configured staging email provider or fail closed."""

    resend_enabled = _strict_env_bool("SENTINEL_RESEND_ENABLED", default=False)
    brevo_enabled = _strict_env_bool("SENTINEL_BREVO_ENABLED", default=False)
    enabled_count = int(resend_enabled) + int(brevo_enabled)
    if enabled_count == 0:
        return DisabledEmailTransport()
    if enabled_count > 1:
        raise RuntimeError("EMAIL_PROVIDER_MULTIPLE_ENABLED")

    environment = os.getenv("SENTINEL_ENV", "development").strip().lower()
    if environment != "staging":
        raise RuntimeError("EMAIL_PROVIDER_STAGING_ONLY")

    try:
        if resend_enabled:
            api_key = os.getenv("SENTINEL_RESEND_API_KEY", "")
            from_address = os.getenv("SENTINEL_RESEND_FROM_ADDRESS", "")
            if not api_key or not from_address:
                raise RuntimeError("RESEND_NOT_CONFIGURED")
            raw_recipients = os.getenv("SENTINEL_RESEND_ALLOWED_RECIPIENTS", "")
            allowed_recipients = tuple(recipient.strip() for recipient in raw_recipients.split(",")) if raw_recipients.strip() else ()
            return ResendEmailTransport(ResendConfig(
                api_key=api_key, from_address=from_address, allowed_recipients=allowed_recipients,
            ))

        api_key = os.getenv("SENTINEL_BREVO_API_KEY", "")
        from_address = os.getenv("SENTINEL_BREVO_FROM_ADDRESS", "")
        from_name = os.getenv("SENTINEL_BREVO_FROM_NAME", "SENTINEL")
        if not api_key or not from_address:
            raise RuntimeError("BREVO_NOT_CONFIGURED")
        return BrevoEmailTransport(
            BrevoConfig(api_key=api_key, from_address=from_address, from_name=from_name)
        )
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
