from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from urllib.error import URLError

import pytest

import app.core.email_provider as email_module
import app.core.posthog_telemetry as posthog_module
from app.core.companion_observability import CompanionTelemetryEvent
from app.core.email_provider import (
    EmailMessage,
    EmailProviderUnavailable,
    ResendConfig,
    ResendEmailTransport,
    TestEmailTransport as InMemoryEmailTransport,
    configured_email_transport,
)
from app.core.json_bounds import validate_bounded_json
from app.core.posthog_telemetry import (
    PostHogCompanionTelemetrySink,
    PostHogConfig,
    PostHogHttpTransport,
    configured_posthog_sink,
)
from app.core.request_limits import (
    MAX_REQUEST_BODY_BYTES,
    MIN_REQUEST_BODY_BYTES,
    RequestBodyLimitMiddleware,
    RequestBodyTooLarge,
    _request_id,
)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_bytes": 0},
        {"max_bytes": 100, "max_depth": 0},
        {"max_bytes": 100, "max_nodes": 0},
        {"max_bytes": 100, "max_key_bytes": 0},
        {"max_bytes": 100, "max_string_bytes": 0},
    ],
)
def test_json_bounds_reject_invalid_limit_configuration(kwargs) -> None:
    with pytest.raises(ValueError, match="JSON_LIMIT_CONFIGURATION_INVALID"):
        validate_bounded_json({}, **kwargs)


@pytest.mark.parametrize(
    ("value", "kwargs", "error"),
    [
        ([1, 2, 3], {"max_bytes": 100, "max_nodes": 2}, "JSON_NODE_LIMIT"),
        (float("nan"), {"max_bytes": 100}, "JSON_NUMBER_INVALID"),
        (float("inf"), {"max_bytes": 100}, "JSON_NUMBER_INVALID"),
        ("é" * 5, {"max_bytes": 100, "max_string_bytes": 9}, "JSON_STRING_LIMIT"),
        ({1: "value"}, {"max_bytes": 100}, "JSON_KEY_INVALID"),
        ({"é" * 5: 1}, {"max_bytes": 100, "max_key_bytes": 9}, "JSON_KEY_LIMIT"),
        ({1, 2}, {"max_bytes": 100}, "JSON_TYPE_INVALID"),
    ],
)
def test_json_bounds_reject_node_number_string_key_and_type_abuse(value, kwargs, error) -> None:
    with pytest.raises(ValueError, match=error):
        validate_bounded_json(value, **kwargs)


def test_json_bounds_accept_all_json_scalar_and_container_types_without_coercion() -> None:
    value = {
        "none": None,
        "bool": True,
        "int": 1,
        "float": 1.5,
        "string": "ok",
        "list": [False, 2],
        "dict": {"nested": "value"},
    }
    assert validate_bounded_json(value, max_bytes=1024) is value


@pytest.mark.parametrize("limit", [MIN_REQUEST_BODY_BYTES - 1, MAX_REQUEST_BODY_BYTES + 1])
def test_request_limit_middleware_rejects_invalid_constructor_limit(limit: int) -> None:
    async def app(_scope, _receive, _send):
        raise AssertionError("must not run")

    with pytest.raises(ValueError, match="INVALID_REQUEST_BODY_LIMIT"):
        RequestBodyLimitMiddleware(app, max_body_bytes=limit)


def test_request_id_rejects_non_ascii_control_and_overlong_values() -> None:
    valid = {"headers": [(b"x-request-id", b"safe-id")]}
    assert _request_id(valid) == "safe-id"
    for raw in (b"bad\xff", b"bad\nvalue", b"x" * 129, b""):
        generated = _request_id({"headers": [(b"x-request-id", raw)]})
        assert generated != raw.decode("ascii", errors="ignore")
        assert len(generated) == 36


def test_request_limit_passes_non_http_scope_untouched() -> None:
    called = []

    async def app(scope, receive, send):
        called.append(scope["type"])

    middleware = RequestBodyLimitMiddleware(app, max_body_bytes=MIN_REQUEST_BODY_BYTES)
    asyncio.run(middleware({"type": "websocket"}, lambda: None, lambda _m: None))
    assert called == ["websocket"]


def test_request_limit_rejects_malformed_content_length_without_app_call() -> None:
    sent = []
    called = False

    async def app(_scope, _receive, _send):
        nonlocal called
        called = True

    async def send(message):
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(app, max_body_bytes=MIN_REQUEST_BODY_BYTES)
    for raw in (b"not-int", b"\xff"):
        sent.clear()
        scope = {"type": "http", "headers": [(b"content-length", raw), (b"x-request-id", b"req-1")]}
        asyncio.run(middleware(scope, lambda: None, send))
        assert sent[0]["status"] == 400
        assert b"INVALID_CONTENT_LENGTH" in sent[1]["body"]
    assert called is False


def test_streaming_body_limit_rejects_without_content_length_before_response() -> None:
    sent = []
    chunks = iter(
        [
            {"type": "http.request", "body": b"x" * 40_000, "more_body": True},
            {"type": "http.request", "body": b"x" * 30_000, "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def app(_scope, receive_limited, _send):
        await receive_limited()
        await receive_limited()

    middleware = RequestBodyLimitMiddleware(app, max_body_bytes=MIN_REQUEST_BODY_BYTES)
    asyncio.run(middleware({"type": "http", "headers": []}, receive, send))
    assert sent[0]["status"] == 413
    assert b"REQUEST_BODY_TOO_LARGE" in sent[1]["body"]


def test_streaming_overflow_after_response_start_is_not_rewritten() -> None:
    chunks = iter([{"type": "http.request", "body": b"x" * 70_000, "more_body": False}])
    sent = []

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def app(_scope, receive_limited, send_tracked):
        await send_tracked({"type": "http.response.start", "status": 200, "headers": []})
        await receive_limited()

    middleware = RequestBodyLimitMiddleware(app, max_body_bytes=MIN_REQUEST_BODY_BYTES)
    with pytest.raises(RequestBodyTooLarge):
        asyncio.run(middleware({"type": "http", "headers": []}, receive, send))
    assert sent == [{"type": "http.response.start", "status": 200, "headers": []}]


@pytest.mark.parametrize(
    ("to", "subject", "text", "error"),
    [
        ("bad", "subject", "body", "EMAIL_RECIPIENT_INVALID"),
        ("ok@example.com", "", "body", "EMAIL_SUBJECT_INVALID"),
        ("ok@example.com", "bad\rsubject", "body", "EMAIL_SUBJECT_INVALID"),
        ("ok@example.com", "subject", "", "EMAIL_TEXT_INVALID"),
        ("ok@example.com", "subject", "x" * 32769, "EMAIL_TEXT_INVALID"),
    ],
)
def test_email_message_rejects_unbounded_or_header_injectable_content(to, subject, text, error) -> None:
    with pytest.raises(ValueError, match=error):
        EmailMessage(to, subject, text)


@pytest.mark.parametrize("max_messages", [0, -1, 257])
def test_in_memory_email_transport_rejects_invalid_buffer_size(max_messages: int) -> None:
    with pytest.raises(ValueError, match="EMAIL_TEST_BUFFER_INVALID"):
        InMemoryEmailTransport(max_messages=max_messages)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"api_key": "bad"}, "RESEND_API_KEY_INVALID"),
        ({"from_address": "bad"}, "RESEND_FROM_ADDRESS_INVALID"),
        ({"endpoint": "http://api.resend.com/emails"}, "RESEND_ENDPOINT_INVALID"),
        ({"endpoint": "https://user:pass@api.resend.com/emails"}, "RESEND_ENDPOINT_INVALID"),
    ],
)
def test_resend_config_rejects_invalid_credentials_sender_and_endpoint(kwargs, error) -> None:
    values = {
        "api_key": "re_test_secret_key_123",
        "from_address": "sentinel@example.com",
        "endpoint": "https://api.resend.com/emails",
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=error):
        ResendConfig(**values)


@pytest.mark.parametrize("timeout", [0, -1, 21])
def test_resend_transport_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="RESEND_TIMEOUT_INVALID"):
        ResendEmailTransport(
            ResendConfig(api_key="re_test_secret_key_123", from_address="sentinel@example.com"),
            timeout_seconds=timeout,
        )


class _Response:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self.raw


@pytest.mark.parametrize(
    ("raw", "error"),
    [
        (b"x" * 65_537, "RESEND_RESPONSE_TOO_LARGE"),
        (b"{", "RESEND_RESPONSE_INVALID"),
        (b"[]", "RESEND_RESPONSE_INVALID"),
        (b'{"id":"bad space"}', "RESEND_RESPONSE_INVALID"),
    ],
)
def test_resend_transport_bounds_provider_responses(monkeypatch, raw: bytes, error: str) -> None:
    monkeypatch.setattr(email_module, "urlopen", lambda *_a, **_k: _Response(raw))
    transport = ResendEmailTransport(
        ResendConfig(api_key="re_test_secret_key_123", from_address="sentinel@example.com")
    )
    with pytest.raises(EmailProviderUnavailable, match=error):
        transport.send(EmailMessage("to@example.com", "Subject", "Body"))


def test_resend_transport_maps_network_failure_and_accepts_valid_provider_id(monkeypatch) -> None:
    transport = ResendEmailTransport(
        ResendConfig(api_key="re_test_secret_key_123", from_address="sentinel@example.com")
    )
    monkeypatch.setattr(
        email_module,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(URLError("private")),
    )
    with pytest.raises(EmailProviderUnavailable, match="RESEND_UNAVAILABLE"):
        transport.send(EmailMessage("to@example.com", "Subject", "Body"))

    captured = {}
    def open_ok(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(b'{"id":"email_123456"}')
    monkeypatch.setattr(email_module, "urlopen", open_ok)
    assert transport.send(EmailMessage("to@example.com", "Subject", "Body")) == "email_123456"
    assert captured["timeout"] == 8.0
    assert captured["request"].full_url == "https://api.resend.com/emails"


def test_resend_activation_parser_is_strict_and_accepts_complete_staging_configuration(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "yes")
    with pytest.raises(RuntimeError, match="SENTINEL_RESEND_ENABLED_INVALID"):
        configured_email_transport()

    monkeypatch.setenv("SENTINEL_RESEND_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_ENV", "staging")
    monkeypatch.setenv("SENTINEL_RESEND_API_KEY", "bad")
    monkeypatch.setenv("SENTINEL_RESEND_FROM_ADDRESS", "sentinel@example.com")
    with pytest.raises(RuntimeError, match="RESEND_API_KEY_INVALID"):
        configured_email_transport()

    monkeypatch.setenv("SENTINEL_RESEND_API_KEY", "re_test_secret_key_123")
    assert isinstance(configured_email_transport(), ResendEmailTransport)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"project_key": ""}, "POSTHOG_PROJECT_KEY_INVALID"),
        ({"project_key": "x" * 257}, "POSTHOG_PROJECT_KEY_INVALID"),
        ({"region": "ap"}, "POSTHOG_REGION_INVALID"),
        ({"environment": "STAGING"}, "POSTHOG_ENVIRONMENT_INVALID"),
        ({"environment": "production"}, "POSTHOG_STAGING_ONLY"),
        ({"release": ""}, "POSTHOG_RELEASE_INVALID"),
        ({"release": "bad release"}, "POSTHOG_RELEASE_INVALID"),
        ({"source_sha": "A" * 40}, "POSTHOG_SOURCE_SHA_INVALID"),
    ],
)
def test_posthog_config_rejects_unbounded_or_nonstaging_identity(kwargs, error) -> None:
    values = {
        "project_key": "phc_test",
        "region": "us",
        "environment": "staging",
        "release": "1.0.0-rc2",
        "source_sha": "a" * 40,
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=error):
        PostHogConfig(**values)


@pytest.mark.parametrize("timeout", [0, -1, 16])
def test_posthog_http_transport_rejects_invalid_timeout(timeout: float) -> None:
    config = PostHogConfig("phc_test", "us", "staging", "rc2", "a" * 40)
    with pytest.raises(ValueError, match="POSTHOG_TIMEOUT_INVALID"):
        PostHogHttpTransport(config, timeout_seconds=timeout)


def test_posthog_http_transport_uses_literal_region_endpoint_and_bounds_response(monkeypatch) -> None:
    config = PostHogConfig("phc_test", "eu", "staging", "rc2", "a" * 40)
    transport = PostHogHttpTransport(config)
    captured = {}

    def open_ok(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return _Response(b"{}")

    monkeypatch.setattr(posthog_module, "urlopen", open_ok)
    transport.capture({"event": "companion.test"})
    assert captured == {"url": "https://eu.i.posthog.com/capture/", "timeout": 5.0}

    monkeypatch.setattr(posthog_module, "urlopen", lambda *_a, **_k: _Response(b"x" * 65_537))
    with pytest.raises(RuntimeError, match="POSTHOG_RESPONSE_TOO_LARGE"):
        transport.capture({"event": "companion.test"})

    monkeypatch.setattr(
        posthog_module,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(URLError("private")),
    )
    with pytest.raises(RuntimeError, match="POSTHOG_UNAVAILABLE"):
        transport.capture({"event": "companion.test"})


def test_posthog_sink_ignores_nonallowlisted_attributes_and_counts_outcomes() -> None:
    captured = []
    transport = SimpleNamespace(capture=lambda payload: captured.append(payload))
    config = PostHogConfig("phc_test", "us", "staging", "rc2", "a" * 40)
    sink = PostHogCompanionTelemetrySink(config, transport)
    event = CompanionTelemetryEvent.create(
        "companion.test",
        datetime.now(UTC),
        {"status": "ok", "device_id": "private", "token": "secret"},
    )
    sink.record(event)
    assert sink.delivered_events == 1
    assert sink.dropped_events == 0
    assert captured[0]["properties"]["status"] == "ok"
    assert "device_id" not in captured[0]["properties"]
    assert "token" not in captured[0]["properties"]


def test_posthog_activation_parser_is_strict_and_accepts_complete_staging_configuration(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_POSTHOG_ENABLED", "yes")
    with pytest.raises(RuntimeError, match="SENTINEL_POSTHOG_ENABLED_INVALID"):
        configured_posthog_sink()

    monkeypatch.setenv("SENTINEL_POSTHOG_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_POSTHOG_PROJECT_KEY", "phc_test")
    monkeypatch.setenv("SENTINEL_RELEASE", "rc2")
    monkeypatch.setenv("SENTINEL_SOURCE_SHA", "A" * 40)
    monkeypatch.setenv("SENTINEL_POSTHOG_REGION", "US")
    monkeypatch.setenv("SENTINEL_ENV", "STAGING")
    sink = configured_posthog_sink()
    assert sink is not None
    assert sink.config.region == "us"
    assert sink.config.environment == "staging"
    assert sink.config.source_sha == "a" * 40
