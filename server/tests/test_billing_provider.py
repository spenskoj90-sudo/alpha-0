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

from app.core.billing import BillingService, BillingWebhookEvent
from app.core.billing_provider import (
    HmacBillingProviderAdapter,
    ProviderSubscriptionSnapshot,
    ProviderVerificationError,
)
from app.core.p1_runtime import BillingState
from app.core.store import MemoryStore
from app.main import app


SECRET = b"sentinel-provider-test-secret-32-bytes"


def signed_header(secret: bytes, body: bytes, timestamp: int) -> str:
    digest = hmac.new(
        secret,
        str(timestamp).encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def event_body(provider_subscription_id: str, *, status: str = "ACTIVE", event_id: str | None = None) -> bytes:
    payload = {
        "event_id": event_id or f"evt-{uuid.uuid4().hex}",
        "provider_subscription_id": provider_subscription_id,
        "status": status,
        "occurred_at": datetime.now(UTC).isoformat(),
        "external_reference": "provider-event",
        "payload": {"source": "deterministic-test"},
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_hmac_provider_verifies_exact_body_and_rejects_tamper_and_stale_delivery() -> None:
    adapter = HmacBillingProviderAdapter("signed-test", SECRET)
    body = event_body("sub-verified")
    timestamp = int(time.time())
    signature = signed_header(SECRET, body, timestamp)

    verified = adapter.verify_webhook(body, signature)
    assert verified.provider == "signed-test"
    assert verified.target_state is BillingState.ACTIVE
    assert verified.verification_method == "hmac-sha256-v1"

    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_SIGNATURE_INVALID"):
        adapter.verify_webhook(body + b" ", signature)

    stale_now = datetime.fromtimestamp(timestamp, UTC) + timedelta(seconds=301)
    with pytest.raises(ProviderVerificationError, match="PROVIDER_WEBHOOK_SIGNATURE_STALE"):
        adapter.verify_webhook(body, signature, now=stale_now)


def test_external_provider_cannot_fall_back_to_legacy_shared_token_boundary() -> None:
    local = MemoryStore()
    service = BillingService(local)
    service.create_subscription(
        "billing-user",
        "core-plus",
        provider="signed-test",
        provider_subscription_id="sub-legacy-bypass",
    )

    with pytest.raises(ValueError, match="UNVERIFIED_PROVIDER_EVENT"):
        service.apply_webhook(
            BillingWebhookEvent(
                event_id="evt-legacy-bypass",
                provider="signed-test",
                provider_subscription_id="sub-legacy-bypass",
                target_state=BillingState.ACTIVE,
                occurred_at=datetime.now(UTC),
            )
        )


def test_verified_event_and_reconciliation_drive_server_feature_grants() -> None:
    local = MemoryStore()
    service = BillingService(local)
    service.create_subscription(
        "billing-user",
        "core-plus",
        provider="signed-test",
        provider_subscription_id="sub-reconcile",
    )
    adapter = HmacBillingProviderAdapter("signed-test", SECRET)
    body = event_body("sub-reconcile", event_id="evt-verified-active")
    timestamp = int(time.time())
    verified = adapter.verify_webhook(body, signed_header(SECRET, body, timestamp))

    activated = service.apply_verified_webhook(verified)
    assert activated["subscription"]["status"] == "ACTIVE"
    assert service.feature_entitlements("billing-user") == ("companion", "core")

    snapshot = ProviderSubscriptionSnapshot(
        provider="signed-test",
        provider_subscription_id="sub-reconcile",
        target_state=BillingState.PAST_DUE,
        observed_at=datetime.now(UTC) + timedelta(seconds=1),
        revision="provider-revision-2",
        external_reference="reconcile-2",
    )
    reconciliation_adapter = HmacBillingProviderAdapter(
        "signed-test",
        SECRET,
        snapshot_reader=lambda _subscription_id: snapshot,
    )
    reconciled = service.reconcile_provider(reconciliation_adapter, "sub-reconcile")
    assert reconciled["subscription"]["status"] == "PAST_DUE"
    assert reconciled["verification_method"] == "provider-reconciliation"
    assert service.feature_entitlements("billing-user") == ()

    replay = service.reconcile_provider(reconciliation_adapter, "sub-reconcile")
    assert replay["accepted"] is False
    assert replay["duplicate"] is True


def test_signed_provider_http_ingress_and_feature_readback(monkeypatch) -> None:
    provider = "signed-test"
    secret_text = "sentinel-provider-route-secret-32bytes"
    secret = secret_text.encode("utf-8")
    monkeypatch.setenv("SENTINEL_BILLING_HMAC_PROVIDER", provider)
    monkeypatch.setenv("SENTINEL_BILLING_HMAC_WEBHOOK_SECRET", secret_text)
    monkeypatch.setenv("SENTINEL_BILLING_WEBHOOK_TOKEN", "legacy-internal-token")

    client = TestClient(app)
    suffix = uuid.uuid4().hex
    registration = client.post(
        "/v1/auth/register",
        json={
            "email": f"provider-{suffix}@example.com",
            "password": f"Correct-Horse-Battery-Staple-{suffix}",
        },
    )
    assert registration.status_code == 200
    auth = {"Authorization": f"Bearer {registration.json()['session_token']}"}

    provider_subscription_id = f"signed-{suffix}"
    created = client.post(
        "/v1/billing/subscriptions",
        headers=auth,
        json={
            "plan_code": "core-plus",
            "provider": provider,
            "provider_subscription_id": provider_subscription_id,
        },
    )
    assert created.status_code == 200
    body = event_body(provider_subscription_id, event_id=f"evt-signed-{suffix}")
    timestamp = int(time.time())

    invalid = client.post(
        f"/v1/billing/provider-webhooks/{provider}",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Billing-Signature": f"t={timestamp},v1={'0' * 64}",
        },
    )
    assert invalid.status_code == 401

    accepted = client.post(
        f"/v1/billing/provider-webhooks/{provider}",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Billing-Signature": signed_header(secret, body, timestamp),
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["subscription"]["status"] == "ACTIVE"
    assert accepted.json()["verification_method"] == "hmac-sha256-v1"

    features = client.get("/v1/billing/features", headers=auth)
    assert features.status_code == 200
    assert features.json() == {"features": ["companion", "core"]}

    replay = client.post(
        f"/v1/billing/provider-webhooks/{provider}",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Billing-Signature": signed_header(secret, body, timestamp),
        },
    )
    assert replay.status_code == 200
    assert replay.json()["duplicate"] is True

    bypass_subscription_id = f"bypass-{suffix}"
    bypass_created = client.post(
        "/v1/billing/subscriptions",
        headers=auth,
        json={
            "plan_code": "core-plus",
            "provider": provider,
            "provider_subscription_id": bypass_subscription_id,
        },
    )
    assert bypass_created.status_code == 200
    legacy = client.post(
        f"/v1/billing/webhooks/{provider}",
        headers={"X-Billing-Webhook-Token": "legacy-internal-token"},
        json={
            "event_id": f"evt-legacy-{suffix}",
            "provider_subscription_id": bypass_subscription_id,
            "status": "ACTIVE",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert legacy.status_code == 400
    assert legacy.json()["code"] == "UNVERIFIED_PROVIDER_EVENT"
