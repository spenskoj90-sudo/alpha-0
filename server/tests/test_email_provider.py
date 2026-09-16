from __future__ import annotations

import pytest

from app.core.email_provider import (
    DisabledEmailTransport,
    EmailMessage,
    EmailProviderUnavailable,
    ResendConfig,
    TestEmailTransport as InMemoryEmailTransport,
    configured_email_transport,
)


def test_email_message_is_bounded_and_test_transport_never_needs_network() -> None:
    transport = InMemoryEmailTransport(max_messages=2)
    first = EmailMessage("first@example.com", "SENTINEL test", "first body")
    second = EmailMessage("second@example.com", "SENTINEL test", "second body")
    third = EmailMessage("third@example.com", "SENTINEL test", "third body")

    assert transport.send(first) == "test-email-1"
    assert transport.send(second) == "test-email-2"
    assert transport.send(third) == "test-email-2"
    assert transport.snapshot() == (second, third)

    with pytest.raises(ValueError, match="EMAIL_RECIPIENT_INVALID"):
        EmailMessage("not-an-email", "subject", "body")
    with pytest.raises(ValueError, match="EMAIL_SUBJECT_INVALID"):
        EmailMessage("ok@example.com", "bad\nsubject", "body")


def test_disabled_email_transport_fails_closed() -> None:
    transport = DisabledEmailTransport()
    with pytest.raises(EmailProviderUnavailable, match="EMAIL_PROVIDER_UNAVAILABLE"):
        transport.send(EmailMessage("test@example.com", "Subject", "Body"))


def test_resend_config_hides_key_and_requires_https() -> None:
    config = ResendConfig(
        api_key="re_test_secret_key_123",
        from_address="sentinel@example.com",
    )
    assert "re_test_secret_key_123" not in repr(config)

    with pytest.raises(ValueError, match="RESEND_ENDPOINT_INVALID"):
        ResendConfig(
            api_key="re_test_secret_key_123",
            from_address="sentinel@example.com",
            endpoint="http://api.resend.com/emails",
        )


def test_resend_is_disabled_by_default_and_staging_only(monkeypatch) -> None:
    for name in (
        "SENTINEL_RESEND_ENABLED",
        "SENTINEL_RESEND_API_KEY",
        "SENTINEL_RESEND_FROM_ADDRESS",
    ):
        monkeypatch.delenv(name, raising=False)
    assert isinstance(configured_email_transport(), DisabledEmailTransport)

    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_ENV", "production")
    with pytest.raises(RuntimeError, match="RESEND_STAGING_ONLY"):
        configured_email_transport()

    monkeypatch.setenv("SENTINEL_ENV", "staging")
    with pytest.raises(RuntimeError, match="RESEND_NOT_CONFIGURED"):
        configured_email_transport()
