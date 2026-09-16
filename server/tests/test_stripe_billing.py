from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

import pytest

from app.core.billing import BillingService
from app.core.billing_provider import ProviderEventIgnored, ProviderVerificationError
from app.core.stripe_billing import (
    StripeBillingProviderAdapter,
    StripeConfig,
    configured_stripe_adapter,
)
from app.core.store import MemoryStore


class FakeStripeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str], str | None]] = []
        self.responses: dict[tuple[str, str], dict[str, Any]] = {}

    def request(
        self,
        method: str,
        path: str,
        fields: Mapping[str, str] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        normalized = dict(fields or {})
        self.calls.append((method, path, normalized, idempotency_key))
        return dict(self.responses[(method, path)])


def stripe_config(*, livemode: bool = False) -> StripeConfig:
    return StripeConfig(
        secret_key=("sk_live_abcdefghijklmnop" if livemode else "sk_test_abcdefghijklmnop"),
        webhook_secret="whsec_abcdefghijklmnop",
        price_ids={"core-plus": "price_1234567890"},
        success_url="https://staging.example.test/account?checkout=success",
        cancel_url="https://staging.example.test/account?checkout=cancel",
        livemode=livemode,
    )


def sign_stripe(body: bytes, timestamp: int, secret: str = "whsec_abcdefghijklmnop") -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        str(timestamp).encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def subscription_event(
    local_subscription_id: str,
    *,
    provider_subscription_id: str = "sub_1234567890",
    status: str = "active",
    event_type: str = "customer.subscription.updated",
    event_id: str | None = None,
    created: int | None = None,
    livemode: bool = False,
) -> bytes:
    payload = {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "created": created or int(time.time()),
        "livemode": livemode,
        "data": {
            "object": {
                "id": provider_subscription_id,
                "status": status,
                "metadata": {"sentinel_subscription_id": local_subscription_id},
            }
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_checkout_is_server_owned_and_idempotent_per_local_subscription() -> None:
    transport = FakeStripeTransport()
    transport.responses[("POST", "/checkout/sessions")] = {
        "id": "cs_test_1234567890",
        "url": "https://checkout.stripe.com/c/pay/cs_test_1234567890",
        "livemode": False,
    }
    adapter = StripeBillingProviderAdapter(stripe_config(), transport)
    local_id = str(uuid.uuid4())

    checkout = adapter.create_checkout_session(local_id, "core-plus")

    assert checkout.session_id == "cs_test_1234567890"
    assert checkout.livemode is False
    assert transport.calls == [
        (
            "POST",
            "/checkout/sessions",
            {
                "mode": "subscription",
                "line_items[0][price]": "price_1234567890",
                "line_items[0][quantity]": "1",
                "success_url": "https://staging.example.test/account?checkout=success",
                "cancel_url": "https://staging.example.test/account?checkout=cancel",
                "client_reference_id": local_id,
                "metadata[sentinel_subscription_id]": local_id,
                "subscription_data[metadata][sentinel_subscription_id]": local_id,
            },
            f"sentinel-checkout:{local_id}",
        )
    ]


def test_signed_stripe_subscription_binds_local_pending_row_and_controls_features() -> None:
    store = MemoryStore()
    service = BillingService(store)
    local = service.create_subscription("stripe-user", "core-plus", provider="stripe")
    assert local["status"] == "PENDING"
    assert service.feature_entitlements("stripe-user") == ()

    adapter = StripeBillingProviderAdapter(stripe_config(), FakeStripeTransport())
    created = int(time.time())
    active_body = subscription_event(
        local["id"],
        status="active",
        event_type="customer.subscription.created",
        event_id="evt_active_123456",
        created=created,
    )
    verified = adapter.verify_webhook(active_body, sign_stripe(active_body, created))
    result = service.apply_verified_webhook(verified)

    assert result["subscription"]["provider_subscription_id"] == "sub_1234567890"
    assert result["subscription"]["status"] == "ACTIVE"
    assert result["verification_method"] == "stripe-signature-v1"
    assert service.feature_entitlements("stripe-user") == ("companion", "core")

    past_due_body = subscription_event(
        local["id"],
        status="past_due",
        event_id="evt_past_due_123456",
        created=created + 1,
    )
    past_due = adapter.verify_webhook(
        past_due_body,
        sign_stripe(past_due_body, created + 1),
        now=datetime.fromtimestamp(created + 1, UTC),
    )
    downgraded = service.apply_verified_webhook(past_due)
    assert downgraded["subscription"]["status"] == "PAST_DUE"
    assert service.feature_entitlements("stripe-user") == ()


def test_signed_past_due_before_activation_never_grants_paid_feature() -> None:
    store = MemoryStore()
    service = BillingService(store)
    local = service.create_subscription("stripe-preactive", "core-plus", provider="stripe")
    adapter = StripeBillingProviderAdapter(stripe_config(), FakeStripeTransport())
    timestamp = int(time.time())
    body = subscription_event(
        local["id"],
        status="incomplete",
        event_id="evt_incomplete_123456",
        created=timestamp,
    )

    result = service.apply_verified_webhook(
        adapter.verify_webhook(body, sign_stripe(body, timestamp))
    )
    assert result["subscription"]["status"] == "PAST_DUE"
    assert service.feature_entitlements("stripe-preactive") == ()


def test_stripe_signature_tamper_staleness_mode_and_unrelated_events_fail_closed() -> None:
    adapter = StripeBillingProviderAdapter(stripe_config(), FakeStripeTransport())
    local_id = str(uuid.uuid4())
    timestamp = int(time.time())
    body = subscription_event(local_id, created=timestamp)
    signature = sign_stripe(body, timestamp)

    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_SIGNATURE_INVALID"):
        adapter.verify_webhook(body + b" ", signature)

    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_SIGNATURE_STALE"):
        adapter.verify_webhook(
            body,
            signature,
            now=datetime.fromtimestamp(timestamp, UTC) + timedelta(seconds=301),
        )

    live_body = subscription_event(local_id, created=timestamp, livemode=True)
    with pytest.raises(ProviderVerificationError, match="STRIPE_MODE_MISMATCH"):
        adapter.verify_webhook(live_body, sign_stripe(live_body, timestamp))

    ignored_payload = {
        "id": "evt_ignored_123456",
        "type": "checkout.session.completed",
        "created": timestamp,
        "livemode": False,
        "data": {"object": {"id": "cs_test_ignored"}},
    }
    ignored_body = json.dumps(ignored_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    with pytest.raises(ProviderEventIgnored, match="STRIPE_EVENT_IGNORED"):
        adapter.verify_webhook(ignored_body, sign_stripe(ignored_body, timestamp))


def test_stripe_snapshot_reconciliation_maps_provider_state_without_customer_payload() -> None:
    transport = FakeStripeTransport()
    transport.responses[("GET", "/subscriptions/sub_1234567890")] = {
        "id": "sub_1234567890",
        "status": "past_due",
        "livemode": False,
        "current_period_end": 1_800_000_000,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "customer": "cus_private_not_forwarded",
    }
    adapter = StripeBillingProviderAdapter(stripe_config(), transport)

    snapshot = adapter.read_subscription("sub_1234567890")

    assert snapshot.target_state.value == "PAST_DUE"
    assert snapshot.payload == {"stripe_status": "past_due"}
    assert "cus_private" not in json.dumps(snapshot.payload)
    assert len(snapshot.revision) == 64


def test_stripe_is_disabled_by_default_and_live_mode_requires_explicit_production_gate(monkeypatch) -> None:
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
    assert configured_stripe_adapter() is None

    monkeypatch.setenv("SENTINEL_STRIPE_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_STRIPE_LIVEMODE", "true")
    monkeypatch.setenv("SENTINEL_ENV", "staging")
    with pytest.raises(RuntimeError, match="STRIPE_LIVE_MODE_NOT_AUTHORIZED"):
        configured_stripe_adapter()
