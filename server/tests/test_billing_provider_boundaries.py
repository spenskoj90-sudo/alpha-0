from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import app.core.billing_provider as provider
from app.core.billing_provider import (
    BillingProviderRegistry,
    HmacBillingProviderAdapter,
    ProviderSubscriptionSnapshot,
    ProviderVerificationError,
)
from app.core.p1_runtime import BillingState


SECRET = b"0123456789abcdef0123456789abcdef"


def _body(*, occurred_at: str | None = None) -> bytes:
    payload = {
        "event_id": "evt-boundary",
        "provider_subscription_id": "sub-boundary",
        "status": "ACTIVE",
        "occurred_at": occurred_at or datetime.now(UTC).isoformat(),
        "payload": {},
    }
    return json.dumps(payload, separators=(",", ":")).encode()


def _signature(body: bytes, timestamp: int) -> str:
    digest = hmac.new(
        SECRET,
        str(timestamp).encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


@pytest.mark.parametrize(
    ("provider_id", "secret", "skew", "error"),
    [
        ("bad provider", SECRET, 300, "INVALID_PROVIDER"),
        ("valid", b"short", 300, "BILLING_PROVIDER_SECRET_TOO_SHORT"),
        ("valid", SECRET, 0, "INVALID_PROVIDER_CLOCK_SKEW"),
    ],
)
def test_hmac_adapter_rejects_invalid_configuration(provider_id, secret, skew, error) -> None:
    with pytest.raises(ValueError, match=error):
        HmacBillingProviderAdapter(provider_id, secret, max_clock_skew_seconds=skew)


def test_hmac_webhook_rejects_body_time_and_signature_failures() -> None:
    adapter = HmacBillingProviderAdapter("signed-test", SECRET)
    now = datetime.now(UTC)
    timestamp = int(now.timestamp())

    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_BODY_INVALID"):
        adapter.verify_webhook(b"", _signature(b"x", timestamp), now=now)
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_BODY_INVALID"):
        adapter.verify_webhook(b"x" * 262_145, _signature(b"x", timestamp), now=now)

    body = _body()
    with pytest.raises(ValueError, match="PROVIDER_VERIFIER_TIME_MUST_BE_AWARE"):
        adapter.verify_webhook(body, _signature(body, timestamp), now=datetime.now())

    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_SIGNATURE_INVALID"):
        adapter.verify_webhook(body, f"t={timestamp},v1={'0' * 64}", now=now)

    malformed = b"{"
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_BODY_INVALID"):
        adapter.verify_webhook(malformed, _signature(malformed, timestamp), now=now)

    list_body = b"[]"
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_BODY_INVALID"):
        adapter.verify_webhook(list_body, _signature(list_body, timestamp), now=now)

    naive_time = _body(occurred_at="2026-09-25T12:00:00")
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_EVENT_TIME_INVALID"):
        adapter.verify_webhook(naive_time, _signature(naive_time, timestamp), now=now)


@pytest.mark.parametrize(
    "signature",
    [
        "",
        "t=1",
        "v1=" + "0" * 64,
        "t=x,v1=" + "0" * 64,
        "t=1,t=2,v1=" + "0" * 64,
        "t=1,v1=not-hex",
        "t=1,v1=" + "0" * 63,
        "broken",
        "t=1,v1=" + "0" * 64 + ",extra=x",
    ],
)
def test_generic_signature_parser_rejects_malformed_headers(signature: str) -> None:
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_SIGNATURE_INVALID"):
        provider._parse_signature(signature)


def test_provider_snapshot_reconciliation_id_is_stable_and_state_sensitive() -> None:
    observed = datetime.now(UTC)
    first = ProviderSubscriptionSnapshot(
        provider="signed-test",
        provider_subscription_id="sub-1",
        target_state=BillingState.ACTIVE,
        observed_at=observed,
        revision="r1",
    )
    same = ProviderSubscriptionSnapshot(
        provider="signed-test",
        provider_subscription_id="sub-1",
        target_state=BillingState.ACTIVE,
        observed_at=observed + timedelta(seconds=1),
        revision="r1",
    )
    changed = ProviderSubscriptionSnapshot(
        provider="signed-test",
        provider_subscription_id="sub-1",
        target_state=BillingState.PAST_DUE,
        observed_at=observed,
        revision="r1",
    )
    assert first.reconciliation_event_id() == same.reconciliation_event_id()
    assert first.reconciliation_event_id() != changed.reconciliation_event_id()
    assert first.reconciliation_event_id().startswith("reconcile:")


@pytest.mark.parametrize(
    ("subscription_id", "snapshot", "error"),
    [
        ("", None, "INVALID_PROVIDER_SUBSCRIPTION_ID"),
        ("x" * 257, None, "INVALID_PROVIDER_SUBSCRIPTION_ID"),
        (
            "sub-1",
            ProviderSubscriptionSnapshot("other", "sub-1", BillingState.ACTIVE, datetime.now(UTC), "r"),
            "PROVIDER_SNAPSHOT_MISMATCH",
        ),
        (
            "sub-1",
            ProviderSubscriptionSnapshot("signed-test", "sub-2", BillingState.ACTIVE, datetime.now(UTC), "r"),
            "PROVIDER_SNAPSHOT_MISMATCH",
        ),
        (
            "sub-1",
            ProviderSubscriptionSnapshot("signed-test", "sub-1", BillingState.ACTIVE, datetime.now(), "r"),
            "PROVIDER_SNAPSHOT_TIME_INVALID",
        ),
        (
            "sub-1",
            ProviderSubscriptionSnapshot("signed-test", "sub-1", BillingState.ACTIVE, datetime.now(UTC), ""),
            "PROVIDER_SNAPSHOT_REVISION_INVALID",
        ),
    ],
)
def test_snapshot_reader_validates_provider_identity_and_freshness(subscription_id, snapshot, error) -> None:
    reader = None if snapshot is None else (lambda _id: snapshot)
    adapter = HmacBillingProviderAdapter("signed-test", SECRET, snapshot_reader=reader)
    invalid_id = not subscription_id or len(subscription_id) > 256
    expected = ValueError if invalid_id or snapshot is not None else RuntimeError
    match = error if expected is ValueError else "PROVIDER_RECONCILIATION_UNAVAILABLE"
    with pytest.raises(expected, match=match):
        adapter.read_subscription(subscription_id)


def test_registry_rejects_invalid_duplicate_and_missing_providers() -> None:
    good = HmacBillingProviderAdapter("signed-test", SECRET)
    registry = BillingProviderRegistry((good,))
    assert registry.providers() == ("signed-test",)
    assert registry.require("signed-test") is good

    with pytest.raises(ValueError, match="BILLING_PROVIDER_ALREADY_REGISTERED"):
        registry.register(good)
    with pytest.raises(KeyError, match="BILLING_PROVIDER_NOT_CONFIGURED"):
        registry.require("missing")

    invalid = SimpleNamespace(provider_id="bad provider")
    with pytest.raises(ValueError, match="INVALID_PROVIDER"):
        BillingProviderRegistry((invalid,))


def test_runtime_registry_requires_complete_generic_provider_configuration(monkeypatch) -> None:
    monkeypatch.delenv("SENTINEL_BILLING_HMAC_PROVIDER", raising=False)
    monkeypatch.delenv("SENTINEL_BILLING_HMAC_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("SENTINEL_STRIPE_ENABLED", raising=False)

    registry = provider.configured_provider_registry()
    assert registry.providers() == ()

    monkeypatch.setenv("SENTINEL_BILLING_HMAC_PROVIDER", "signed-test")
    with pytest.raises(RuntimeError, match="BILLING_PROVIDER_NOT_CONFIGURED"):
        provider.configured_provider_registry()

    monkeypatch.delenv("SENTINEL_BILLING_HMAC_PROVIDER", raising=False)
    monkeypatch.setenv("SENTINEL_BILLING_HMAC_WEBHOOK_SECRET", "secret-only")
    with pytest.raises(RuntimeError, match="BILLING_PROVIDER_NOT_CONFIGURED"):
        provider.configured_provider_registry()
