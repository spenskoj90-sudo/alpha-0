from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from app.core.billing import BillingService
from app.core.billing_provider import ProviderVerificationError
from app.core.p1_runtime import BillingState
from app.core.store import MemoryStore
from app.core.stripe_billing import StripeSandboxWebhookAdapter
from app.main import app

SECRET = "whsec_sentinel_sandbox_test_secret_0123456789"


def stripe_event(subscription_id: str, *, status: str = "active", event_type: str = "customer.subscription.updated", livemode: bool = False, event_id: str | None = None, created: int | None = None) -> bytes:
    payload = {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "object": "event",
        "created": created or int(time.time()),
        "livemode": livemode,
        "type": event_type,
        "data": {"object": {
            "id": subscription_id,
            "object": "subscription",
            "customer": "cus_sentineltest",
            "status": status,
        }},
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def stripe_signature(body: bytes, timestamp: int, *, secret: str = SECRET, extra_bad_v1: bool = False) -> str:
    digest = hmac.new(secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
    prefixes = [f"t={timestamp}"]
    if extra_bad_v1:
        prefixes.append("v1=" + "0" * 64)
    prefixes.append(f"v1={digest}")
    prefixes.append("v0=" + "f" * 64)
    return ",".join(prefixes)


def test_stripe_sandbox_verifies_exact_body_multiple_v1_and_maps_status() -> None:
    adapter = StripeSandboxWebhookAdapter(SECRET)
    now = datetime.now(UTC)
    timestamp = int(now.timestamp())
    body = stripe_event("sub_sentineltest", status="trialing", created=timestamp)
    verified = adapter.verify_webhook(body, stripe_signature(body, timestamp, extra_bad_v1=True), now=now)
    assert verified.provider == "stripe"
    assert verified.target_state is BillingState.ACTIVE
    assert verified.verification_method == "stripe-signature-v1"
    assert verified.payload["livemode"] is False


def test_stripe_sandbox_rejects_live_bad_signature_stale_and_unknown_event() -> None:
    adapter = StripeSandboxWebhookAdapter(SECRET)
    timestamp = int(time.time())
    sandbox = stripe_event("sub_sentineltest", created=timestamp)
    with pytest.raises(ProviderVerificationError, match="SIGNATURE_INVALID"):
        adapter.verify_webhook(sandbox, f"t={timestamp},v1={'0' * 64}")
    with pytest.raises(ProviderVerificationError, match="SIGNATURE_STALE"):
        adapter.verify_webhook(sandbox, stripe_signature(sandbox, timestamp), now=datetime.fromtimestamp(timestamp, UTC) + timedelta(seconds=301))
    live = stripe_event("sub_sentineltest", livemode=True, created=timestamp)
    with pytest.raises(ProviderVerificationError, match="LIVEMODE_MISMATCH"):
        adapter.verify_webhook(live, stripe_signature(live, timestamp))
    unsupported = stripe_event("sub_sentineltest", event_type="invoice.paid", created=timestamp)
    with pytest.raises(ProviderVerificationError, match="EVENT_TYPE_UNSUPPORTED"):
        adapter.verify_webhook(unsupported, stripe_signature(unsupported, timestamp))


def test_distinct_same_state_provider_events_are_retained_without_invalid_transition() -> None:
    store = MemoryStore()
    service = BillingService(store)
    service.create_subscription("user", "core-plus", provider="stripe", provider_subscription_id="sub_same")
    adapter = StripeSandboxWebhookAdapter(SECRET)
    timestamp = int(time.time())
    first_body = stripe_event("sub_same", event_id="evt_first", created=timestamp)
    first = adapter.verify_webhook(first_body, stripe_signature(first_body, timestamp))
    activated = service.apply_verified_webhook(first)
    assert activated["subscription"]["status"] == "ACTIVE"
    second_body = stripe_event("sub_same", event_id="evt_second", created=timestamp + 1)
    second = adapter.verify_webhook(second_body, stripe_signature(second_body, timestamp + 1), now=datetime.fromtimestamp(timestamp + 1, UTC))
    unchanged = service.apply_verified_webhook(second)
    assert unchanged["accepted"] is True
    assert unchanged["unchanged"] is True
    assert store.has_billing_event("evt_second")


def test_stripe_http_ingress_is_sandbox_only_and_drives_features(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_STRIPE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("SENTINEL_STRIPE_EXPECT_LIVEMODE", "false")
    client = TestClient(app)
    suffix = uuid.uuid4().hex
    registration = client.post("/v1/auth/register", json={
        "email": f"stripe-{suffix}@example.com",
        "password": f"Correct-Horse-Battery-Staple-{suffix}",
    })
    assert registration.status_code == 200
    auth = {"Authorization": f"Bearer {registration.json()['session_token']}"}
    sub_id = f"sub_{suffix}"
    created = client.post("/v1/billing/subscriptions", headers=auth, json={
        "plan_code": "core-plus", "provider": "stripe", "provider_subscription_id": sub_id,
    })
    assert created.status_code == 200
    timestamp = int(time.time())
    body = stripe_event(sub_id, event_id=f"evt_{suffix}", created=timestamp)
    accepted = client.post("/v1/billing/stripe/webhook", content=body, headers={
        "Content-Type": "application/json",
        "Stripe-Signature": stripe_signature(body, timestamp),
    })
    assert accepted.status_code == 200
    assert accepted.json()["subscription"]["status"] == "ACTIVE"
    assert accepted.json()["verification_method"] == "stripe-signature-v1"
    features = client.get("/v1/billing/features", headers=auth)
    assert features.status_code == 200
    assert features.json() == {"features": ["companion", "core"]}

    live = stripe_event(sub_id, livemode=True, event_id=f"evt_live_{suffix}", created=timestamp)
    rejected = client.post("/v1/billing/stripe/webhook", content=live, headers={
        "Content-Type": "application/json",
        "Stripe-Signature": stripe_signature(live, timestamp),
    })
    assert rejected.status_code == 401
    assert rejected.json()["code"] == "STRIPE_LIVEMODE_MISMATCH"
