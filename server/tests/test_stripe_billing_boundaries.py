from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.error import URLError

import pytest

import app.core.stripe_billing as stripe_module
from app.core.billing_provider import ProviderEventIgnored, ProviderVerificationError
from app.core.p1_runtime import BillingState
from app.core.stripe_billing import (
    StripeBillingProviderAdapter,
    StripeConfig,
    StripeHttpTransport,
    StripeProviderError,
    configured_stripe_adapter,
)


def _config(*, livemode: bool = False, **overrides) -> StripeConfig:
    values = {
        "secret_key": "sk_live_abcdefghijklmnop" if livemode else "sk_test_abcdefghijklmnop",
        "webhook_secret": "whsec_abcdefghijklmnop",
        "price_ids": {"core-plus": "price_1234567890"},
        "success_url": "https://example.test/success",
        "cancel_url": "https://example.test/cancel",
        "livemode": livemode,
    }
    values.update(overrides)
    return StripeConfig(**values)


def _sign(body: bytes, timestamp: int, secret: str = "whsec_abcdefghijklmnop") -> str:
    digest = hmac.new(
        secret.encode(),
        str(timestamp).encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def _event(**overrides) -> dict:
    local_id = str(uuid.uuid4())
    event = {
        "id": "evt_boundary_123456",
        "type": "customer.subscription.updated",
        "created": int(time.time()),
        "livemode": False,
        "data": {
            "object": {
                "id": "sub_1234567890",
                "status": "active",
                "metadata": {"sentinel_subscription_id": local_id},
            }
        },
    }
    for key, value in overrides.items():
        if key.startswith("subscription__"):
            event["data"]["object"][key.split("__", 1)[1]] = value
        else:
            event[key] = value
    return event


def _body(event: object) -> bytes:
    return json.dumps(event, sort_keys=True, separators=(",", ":")).encode()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"secret_key": "sk_live_wrong_for_test"},
        {"webhook_secret": "bad"},
        {"max_clock_skew_seconds": 0},
        {"max_clock_skew_seconds": 3601},
        {"price_ids": {}},
        {"price_ids": {"bad plan": "price_123456"}},
        {"price_ids": {"core-plus": "bad-price"}},
        {"success_url": "http://example.test/success"},
        {"cancel_url": "https://user:pass@example.test/cancel"},
    ],
)
def test_stripe_config_rejects_unsafe_or_incomplete_authority(kwargs) -> None:
    with pytest.raises(ValueError):
        _config(**kwargs)


@pytest.mark.parametrize("timeout", [0, -1, 31])
def test_http_transport_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="STRIPE_TIMEOUT_INVALID"):
        StripeHttpTransport("sk_test_abcdefghijklmnop", timeout_seconds=timeout)


@pytest.mark.parametrize(
    ("method", "path", "idempotency", "code"),
    [
        ("DELETE", "/subscriptions/x", None, "STRIPE_METHOD_INVALID"),
        ("GET", "subscriptions/x", None, "STRIPE_PATH_INVALID"),
        ("GET", "/subscriptions/../secret", None, "STRIPE_PATH_INVALID"),
        ("POST", "/checkout/sessions", "short", "STRIPE_IDEMPOTENCY_KEY_INVALID"),
    ],
)
def test_http_transport_rejects_unbounded_request_shapes(method, path, idempotency, code) -> None:
    transport = StripeHttpTransport("sk_test_abcdefghijklmnop")
    with pytest.raises(ValueError, match=code):
        transport.request(method, path, {"a": "b"}, idempotency_key=idempotency)


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self.payload


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (b"x" * (1_048_576 + 1), "STRIPE_API_RESPONSE_TOO_LARGE"),
        (b"{not-json", "STRIPE_API_RESPONSE_INVALID"),
        (b"[]", "STRIPE_API_RESPONSE_INVALID"),
    ],
)
def test_http_transport_bounds_and_validates_provider_responses(monkeypatch, payload: bytes, error: str) -> None:
    monkeypatch.setattr(stripe_module, "urlopen", lambda *_args, **_kwargs: _Response(payload))
    transport = StripeHttpTransport("sk_test_abcdefghijklmnop")
    with pytest.raises(StripeProviderError, match=error):
        transport.request("GET", "/subscriptions/sub_123456")


def test_http_transport_maps_network_failure_and_builds_valid_get_post(monkeypatch) -> None:
    transport = StripeHttpTransport("sk_test_abcdefghijklmnop")
    monkeypatch.setattr(
        stripe_module,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("network-private-detail")),
    )
    with pytest.raises(StripeProviderError, match="STRIPE_API_UNAVAILABLE"):
        transport.request("GET", "/subscriptions/sub_123456")

    captured = []

    def fake_open(request, timeout):
        captured.append((request, timeout))
        return _Response(b'{"id":"ok"}')

    monkeypatch.setattr(stripe_module, "urlopen", fake_open)
    assert transport.request("GET", "/objects", {"limit": "1"}) == {"id": "ok"}
    assert transport.request(
        "POST",
        "/objects",
        {"name": "safe"},
        idempotency_key="sentinel-idempotency-1",
    ) == {"id": "ok"}
    assert captured[0][0].full_url.endswith("/objects?limit=1")
    assert captured[0][0].data is None
    assert captured[1][0].data == b"name=safe"
    assert captured[1][0].headers["Idempotency-key"] == "sentinel-idempotency-1"


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "bad", "url": "https://checkout.stripe.com/x", "livemode": False},
        {"id": "cs_valid_123", "url": "http://checkout.stripe.com/x", "livemode": False},
        {"id": "cs_valid_123", "url": "https://checkout.stripe.com/x", "livemode": "false"},
        {"id": "cs_valid_123", "url": "https://checkout.stripe.com/x", "livemode": True},
    ],
)
def test_checkout_rejects_malformed_or_wrong_mode_provider_response(payload) -> None:
    transport = SimpleNamespace(request=lambda *_args, **_kwargs: payload)
    adapter = StripeBillingProviderAdapter(_config(), transport)
    with pytest.raises(StripeProviderError):
        adapter.create_checkout_session(str(uuid.uuid4()), "core-plus")


def test_checkout_rejects_invalid_local_binding_and_unconfigured_plan() -> None:
    adapter = StripeBillingProviderAdapter(_config(), SimpleNamespace(request=lambda *_args, **_kwargs: {}))
    with pytest.raises(ValueError, match="STRIPE_SUBSCRIPTION_BINDING_INVALID"):
        adapter.create_checkout_session("not-a-uuid", "core-plus")
    with pytest.raises(ValueError, match="STRIPE_PLAN_NOT_CONFIGURED"):
        adapter.create_checkout_session(str(uuid.uuid4()), "missing")


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda event: "not-a-dict", "PROVIDER_WEBHOOK_BODY_INVALID"),
        (lambda event: {**event, "id": "bad"}, "PROVIDER_WEBHOOK_BODY_INVALID"),
        (lambda event: {**event, "type": 7}, "PROVIDER_WEBHOOK_BODY_INVALID"),
        (lambda event: {**event, "created": 0}, "PROVIDER_WEBHOOK_EVENT_TIME_INVALID"),
        (lambda event: {**event, "data": []}, "PROVIDER_WEBHOOK_BODY_INVALID"),
        (lambda event: {**event, "data": {"object": {"id": "bad", "status": "active"}}}, "PROVIDER_WEBHOOK_BODY_INVALID"),
        (lambda event: {**event, "data": {"object": {"id": "sub_123456", "status": 7}}}, "PROVIDER_WEBHOOK_BODY_INVALID"),
        (lambda event: {**event, "data": {"object": {"id": "sub_123456", "status": "active", "metadata": []}}}, "PROVIDER_WEBHOOK_BODY_INVALID"),
        (lambda event: {**event, "data": {"object": {"id": "sub_123456", "status": "active", "metadata": {"sentinel_subscription_id": 7}}}}, "STRIPE_SUBSCRIPTION_BINDING_INVALID"),
        (lambda event: {**event, "data": {"object": {"id": "sub_123456", "status": "mystery", "metadata": {}}}}, "STRIPE_SUBSCRIPTION_STATUS_UNSUPPORTED"),
    ],
)
def test_webhook_rejects_malformed_but_signed_provider_payloads(mutation, error) -> None:
    adapter = StripeBillingProviderAdapter(_config())
    timestamp = int(time.time())
    event = mutation(_event(created=timestamp))
    body = _body(event)
    with pytest.raises(ProviderVerificationError, match=error):
        adapter.verify_webhook(body, _sign(body, timestamp), now=datetime.fromtimestamp(timestamp, UTC))


def test_webhook_rejects_empty_oversized_naive_time_bad_json_and_wrong_mode() -> None:
    adapter = StripeBillingProviderAdapter(_config())
    timestamp = int(time.time())

    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_BODY_INVALID"):
        adapter.verify_webhook(b"", "t=1,v1=" + "0" * 64)
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_BODY_INVALID"):
        adapter.verify_webhook(b"x" * (262_144 + 1), "t=1,v1=" + "0" * 64)

    body = _body(_event(created=timestamp))
    with pytest.raises(ValueError, match="PROVIDER_VERIFIER_TIME_MUST_BE_AWARE"):
        adapter.verify_webhook(body, _sign(body, timestamp), now=datetime.now())

    invalid_json = b"{"
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_BODY_INVALID"):
        adapter.verify_webhook(
            invalid_json,
            _sign(invalid_json, timestamp),
            now=datetime.fromtimestamp(timestamp, UTC),
        )

    wrong_mode = _body(_event(created=timestamp, livemode=True))
    with pytest.raises(ProviderVerificationError, match="STRIPE_MODE_MISMATCH"):
        adapter.verify_webhook(
            wrong_mode,
            _sign(wrong_mode, timestamp),
            now=datetime.fromtimestamp(timestamp, UTC),
        )


def test_webhook_supports_multiple_signatures_ignores_unrelated_and_maps_deleted() -> None:
    adapter = StripeBillingProviderAdapter(_config())
    timestamp = int(time.time())
    deleted = _body(
        _event(
            created=timestamp,
            type="customer.subscription.deleted",
            subscription__status="canceled",
        )
    )
    valid = _sign(deleted, timestamp).split("v1=", 1)[1]
    verified = adapter.verify_webhook(
        deleted,
        f"t={timestamp},v1={'0' * 64},v1={valid}",
        now=datetime.fromtimestamp(timestamp, UTC),
    )
    assert verified.target_state is BillingState.CANCELED

    unrelated = _body(_event(created=timestamp, type="invoice.paid"))
    with pytest.raises(ProviderEventIgnored, match="STRIPE_EVENT_IGNORED"):
        adapter.verify_webhook(
            unrelated,
            _sign(unrelated, timestamp),
            now=datetime.fromtimestamp(timestamp, UTC),
        )


@pytest.mark.parametrize(
    ("signature", "error"),
    [
        ("", "PROVIDER_WEBHOOK_SIGNATURE_INVALID"),
        ("t=1", "PROVIDER_WEBHOOK_SIGNATURE_INVALID"),
        ("v1=" + "0" * 64, "PROVIDER_WEBHOOK_SIGNATURE_INVALID"),
        ("t=x,v1=" + "0" * 64, "PROVIDER_WEBHOOK_SIGNATURE_INVALID"),
        ("t=1,t=2,v1=" + "0" * 64, "PROVIDER_WEBHOOK_SIGNATURE_INVALID"),
        ("t=1,v1=bad", "PROVIDER_WEBHOOK_SIGNATURE_INVALID"),
        ("broken-piece", "PROVIDER_WEBHOOK_SIGNATURE_INVALID"),
    ],
)
def test_stripe_signature_parser_fails_closed(signature, error) -> None:
    with pytest.raises(ProviderVerificationError, match=error):
        stripe_module._parse_stripe_signature(signature)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("active", BillingState.ACTIVE),
        ("trialing", BillingState.ACTIVE),
        ("past_due", BillingState.PAST_DUE),
        ("unpaid", BillingState.PAST_DUE),
        ("incomplete", BillingState.PAST_DUE),
        ("paused", BillingState.PAST_DUE),
        ("canceled", BillingState.CANCELED),
        ("incomplete_expired", BillingState.EXPIRED),
    ],
)
def test_stripe_status_mapping_is_explicit(status, expected) -> None:
    assert stripe_module._map_stripe_status(status) is expected


@pytest.mark.parametrize(
    ("provider_id", "payload", "error"),
    [
        ("bad", {}, "INVALID_PROVIDER_SUBSCRIPTION_ID"),
        ("sub_valid123", {"id": "other", "status": "active", "livemode": False}, "STRIPE_SUBSCRIPTION_RESPONSE_INVALID"),
        ("sub_valid123", {"id": "sub_valid123", "status": 7, "livemode": False}, "STRIPE_SUBSCRIPTION_RESPONSE_INVALID"),
        ("sub_valid123", {"id": "sub_valid123", "status": "active", "livemode": True}, "STRIPE_MODE_MISMATCH"),
        ("sub_valid123", {"id": "sub_valid123", "status": "unknown", "livemode": False}, "STRIPE_SUBSCRIPTION_STATUS_UNSUPPORTED"),
    ],
)
def test_subscription_reconciliation_fails_closed_on_invalid_provider_state(provider_id, payload, error) -> None:
    transport = SimpleNamespace(request=lambda *_args, **_kwargs: payload)
    adapter = StripeBillingProviderAdapter(_config(), transport)
    expected = ProviderVerificationError if error == "STRIPE_SUBSCRIPTION_STATUS_UNSUPPORTED" else (ValueError if error == "INVALID_PROVIDER_SUBSCRIPTION_ID" else StripeProviderError)
    with pytest.raises(expected, match=error):
        adapter.read_subscription(provider_id)


def _clear_stripe_env(monkeypatch) -> None:
    for name in (
        "SENTINEL_STRIPE_ENABLED",
        "SENTINEL_STRIPE_LIVEMODE",
        "SENTINEL_STRIPE_ALLOW_LIVE",
        "SENTINEL_STRIPE_SECRET_KEY",
        "SENTINEL_STRIPE_WEBHOOK_SECRET",
        "SENTINEL_STRIPE_CORE_PLUS_PRICE_ID",
        "SENTINEL_STRIPE_SUCCESS_URL",
        "SENTINEL_STRIPE_CANCEL_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_configured_stripe_adapter_requires_strict_complete_configuration(monkeypatch) -> None:
    _clear_stripe_env(monkeypatch)
    monkeypatch.setenv("SENTINEL_STRIPE_ENABLED", "yes")
    with pytest.raises(RuntimeError, match="SENTINEL_STRIPE_ENABLED_INVALID"):
        configured_stripe_adapter()

    _clear_stripe_env(monkeypatch)
    monkeypatch.setenv("SENTINEL_STRIPE_ENABLED", "true")
    with pytest.raises(RuntimeError, match="STRIPE_NOT_CONFIGURED"):
        configured_stripe_adapter()

    monkeypatch.setenv("SENTINEL_STRIPE_SECRET_KEY", "bad")
    monkeypatch.setenv("SENTINEL_STRIPE_WEBHOOK_SECRET", "whsec_abcdefghijklmnop")
    monkeypatch.setenv("SENTINEL_STRIPE_CORE_PLUS_PRICE_ID", "price_1234567890")
    monkeypatch.setenv("SENTINEL_STRIPE_SUCCESS_URL", "https://example.test/success")
    monkeypatch.setenv("SENTINEL_STRIPE_CANCEL_URL", "https://example.test/cancel")
    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY_MODE_MISMATCH"):
        configured_stripe_adapter()

    monkeypatch.setenv("SENTINEL_STRIPE_SECRET_KEY", "sk_test_abcdefghijklmnop")
    adapter = configured_stripe_adapter()
    assert adapter is not None
    assert adapter.config.livemode is False
