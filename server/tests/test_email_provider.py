from __future__ import annotations

import pytest

from app.core.email_provider import (
    BrevoConfig,
    BrevoEmailTransport,
    DisabledEmailTransport,
    EmailMessage,
    EmailProviderUnavailable,
    ResendConfig,
    ResendEmailTransport,
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


def test_email_providers_are_disabled_by_default_and_staging_only(monkeypatch) -> None:
    for name in (
        "SENTINEL_RESEND_ENABLED",
        "SENTINEL_RESEND_API_KEY",
        "SENTINEL_RESEND_FROM_ADDRESS",
        "SENTINEL_BREVO_ENABLED",
        "SENTINEL_BREVO_API_KEY",
        "SENTINEL_BREVO_FROM_ADDRESS",
        "SENTINEL_BREVO_FROM_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
    assert isinstance(configured_email_transport(), DisabledEmailTransport)

    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_ENV", "production")
    with pytest.raises(RuntimeError, match="EMAIL_PROVIDER_STAGING_ONLY"):
        configured_email_transport()

    monkeypatch.setenv("SENTINEL_ENV", "staging")
    with pytest.raises(RuntimeError, match="RESEND_NOT_CONFIGURED"):
        configured_email_transport()

    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "false")
    monkeypatch.setenv("SENTINEL_BREVO_ENABLED", "true")
    with pytest.raises(RuntimeError, match="BREVO_NOT_CONFIGURED"):
        configured_email_transport()


def test_brevo_config_hides_key_and_pins_https_api() -> None:
    config = BrevoConfig(
        api_key="xkeysib-test-secret-key-123456",
        from_address="sentinel@example.com",
    )
    assert "xkeysib-test-secret-key-123456" not in repr(config)

    with pytest.raises(ValueError, match="BREVO_ENDPOINT_INVALID"):
        BrevoConfig(
            api_key="xkeysib-test-secret-key-123456",
            from_address="sentinel@example.com",
            endpoint="https://example.com/v3/smtp/email",
        )

    with pytest.raises(ValueError, match="BREVO_FROM_NAME_INVALID"):
        BrevoConfig(
            api_key="xkeysib-test-secret-key-123456",
            from_address="sentinel@example.com",
            from_name="bad\nname",
        )


def test_brevo_complete_staging_configuration_is_selected(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_ENV", "staging")
    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "false")
    monkeypatch.setenv("SENTINEL_BREVO_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_BREVO_API_KEY", "xkeysib-test-secret-key-123456")
    monkeypatch.setenv("SENTINEL_BREVO_FROM_ADDRESS", "sentinel@example.com")
    assert isinstance(configured_email_transport(), BrevoEmailTransport)


def test_resend_test_sender_requires_explicit_recipient_allowlist() -> None:
    with pytest.raises(ValueError, match="RESEND_SANDBOX_RECIPIENTS_REQUIRED"):
        ResendConfig(api_key="re_test_secret_key_123", from_address="onboarding@resend.dev")


@pytest.mark.parametrize("recipients", [("",), ("invalid",), ("ok@example.com\n",), ("ok@example.com",) * 33])
def test_resend_recipient_allowlist_rejects_invalid_or_unbounded_configuration(recipients) -> None:
    with pytest.raises(ValueError, match="RESEND_ALLOWED_RECIPIENTS_INVALID"):
        ResendConfig(api_key="re_test_secret_key_123", from_address="sentinel@example.com", allowed_recipients=recipients)


def test_resend_blocked_recipient_never_reaches_provider(monkeypatch) -> None:
    def unexpected_network(*args, **kwargs):
        pytest.fail("blocked recipient reached the email provider")

    monkeypatch.setattr("app.core.email_provider.urlopen", unexpected_network)
    monkeypatch.setenv("SENTINEL_ENV", "staging")
    monkeypatch.setenv("SENTINEL_BREVO_ENABLED", "false")
    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_RESEND_API_KEY", "re_test_secret_key_123")
    monkeypatch.setenv("SENTINEL_RESEND_FROM_ADDRESS", "onboarding@resend.dev")
    monkeypatch.setenv("SENTINEL_RESEND_ALLOWED_RECIPIENTS", "delivered@resend.dev")
    with pytest.raises(EmailProviderUnavailable, match="RESEND_RECIPIENT_NOT_ALLOWED"):
        configured_email_transport().send(EmailMessage("someone@example.com", "Subject", "Body"))


def test_resend_domain_transition_uses_same_transport_and_only_configuration(monkeypatch) -> None:
    import json
    from io import BytesIO

    payloads = []

    def provider_response(request, *, timeout):
        assert request.full_url == "https://api.resend.com/emails"
        payloads.append(json.loads(request.data))
        return BytesIO(b'{"id":"email-test-123"}')

    monkeypatch.setattr("app.core.email_provider.urlopen", provider_response)
    monkeypatch.setenv("SENTINEL_ENV", "staging")
    monkeypatch.setenv("SENTINEL_BREVO_ENABLED", "false")
    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_RESEND_API_KEY", "re_test_secret_key_123")
    monkeypatch.setenv("SENTINEL_RESEND_FROM_ADDRESS", "onboarding@resend.dev")
    monkeypatch.setenv("SENTINEL_RESEND_ALLOWED_RECIPIENTS", " delivered@resend.dev ")
    sandbox = configured_email_transport()
    assert isinstance(sandbox, ResendEmailTransport)
    assert sandbox.send(EmailMessage("delivered@resend.dev", "Subject", "Body")) == "email-test-123"

    monkeypatch.setenv("SENTINEL_RESEND_FROM_ADDRESS", "accounts@mail.example.com")
    monkeypatch.setenv("SENTINEL_RESEND_ALLOWED_RECIPIENTS", "")
    owned_domain = configured_email_transport()
    assert isinstance(owned_domain, ResendEmailTransport)
    assert owned_domain.send(EmailMessage("someone@example.com", "Subject", "Body")) == "email-test-123"
    assert payloads == [
        {"from": "SENTINEL <onboarding@resend.dev>", "to": ["delivered@resend.dev"], "subject": "Subject", "text": "Body"},
        {"from": "SENTINEL <accounts@mail.example.com>", "to": ["someone@example.com"], "subject": "Subject", "text": "Body"},
    ]


@pytest.mark.parametrize('provider', ['resend', 'brevo'])
def test_provider_delivers_html_and_plaintext_and_credentials_stay_out_of_repr(monkeypatch, provider):
    import json
    from io import BytesIO
    from app.core.account_notifications import action_email
    payloads = []
    def response(request, *, timeout):
        payloads.append(json.loads(request.data))
        return BytesIO(b'{"id":"test-id","messageId":"test-id"}')
    monkeypatch.setattr('app.core.email_provider.urlopen', response)
    mail = action_email('delivered@resend.dev', '00001234', language='ru')
    transport = (ResendEmailTransport(ResendConfig(api_key='re_fixture_secret_123', from_address='sentinel@example.com')) if provider == 'resend' else BrevoEmailTransport(BrevoConfig(api_key='xkeysib-fixture-secret-123456789', from_address='sentinel@example.com')))
    transport.send(mail)
    assert payloads[0]['text' if provider == 'resend' else 'textContent'] == mail.text
    assert payloads[0]['html' if provider == 'resend' else 'htmlContent'] == mail.html
    assert '00001234' not in repr(mail)
    with pytest.raises(ValueError, match='EMAIL_HTML_INVALID'):
        EmailMessage('ok@example.com', 'subject', 'body', 'я' * 32769)
