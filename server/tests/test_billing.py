from datetime import UTC, datetime, timedelta
import os

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from fastapi.testclient import TestClient

from app.core.billing import BillingService, BillingWebhookEvent
from app.core.p1_runtime import BillingState
from app.core.store import MemoryStore
from app.main import app, store


def test_billing_service_rejects_unknown_plan_and_applies_idempotent_webhook():
    local = MemoryStore()
    service = BillingService(local)
    try:
        service.create_subscription("billing-user", "missing")
    except ValueError as exc:
        assert str(exc) == "UNKNOWN_PLAN"
    else:
        raise AssertionError("unknown plan must fail closed")

    subscription = service.create_subscription("billing-user", "core-plus", provider="test", provider_subscription_id="sub-1")
    now = datetime.now(UTC)
    event = BillingWebhookEvent("evt-1", "test", "sub-1", BillingState.ACTIVE, now)
    first = service.apply_webhook(event)
    assert first["accepted"] is True
    assert first["subscription"]["status"] == "ACTIVE"
    duplicate = service.apply_webhook(event)
    assert duplicate == {"accepted": False, "duplicate": True, "subscription": first["subscription"]}
    assert local.find_subscription_by_provider_id("test", "sub-1")["id"] == subscription["id"]


def test_billing_lifecycle_cannot_reactivate_canceled_subscription():
    local = MemoryStore()
    service = BillingService(local)
    service.create_subscription("billing-user", "core", provider="test", provider_subscription_id="sub-2")
    now = datetime.now(UTC)
    service.apply_webhook(BillingWebhookEvent("evt-2", "test", "sub-2", BillingState.ACTIVE, now))
    service.apply_webhook(BillingWebhookEvent("evt-3", "test", "sub-2", BillingState.CANCELED, now + timedelta(seconds=1)))
    try:
        service.apply_webhook(BillingWebhookEvent("evt-4", "test", "sub-2", BillingState.ACTIVE, now + timedelta(seconds=2)))
    except ValueError as exc:
        assert "INVALID_BILLING_TRANSITION" in str(exc)
    else:
        raise AssertionError("terminal subscription must remain terminal")


def test_billing_api_is_caller_scoped_and_webhook_token_fail_closed(monkeypatch):
    client = TestClient(app)
    email = "billing-api@example.com"
    password = "Correct-Horse-Battery-Staple-billing"
    registration = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 200
    headers = {"Authorization": f"Bearer {registration.json()['session_token']}"}

    plans = client.get("/v1/billing/plans", headers=headers)
    assert plans.status_code == 200
    assert {item["code"] for item in plans.json()["plans"]} == {"core", "core-plus"}

    created = client.post("/v1/billing/subscriptions", headers=headers, json={"plan_code": "core-plus", "provider": "test", "provider_subscription_id": "api-sub-1"})
    assert created.status_code == 200
    assert created.json()["status"] == "PENDING"
    listed = client.get("/v1/billing/subscriptions", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["subscriptions"]] == [created.json()["id"]]

    monkeypatch.delenv("SENTINEL_BILLING_WEBHOOK_TOKEN", raising=False)
    missing_secret = client.post("/v1/billing/webhooks/test", json={"event_id": "api-evt-1", "provider_subscription_id": "api-sub-1", "status": "ACTIVE", "occurred_at": datetime.now(UTC).isoformat()})
    assert missing_secret.status_code == 503
    monkeypatch.setenv("SENTINEL_BILLING_WEBHOOK_TOKEN", "test-secret")
    invalid = client.post("/v1/billing/webhooks/test", headers={"X-Billing-Webhook-Token": "wrong"}, json={"event_id": "api-evt-1", "provider_subscription_id": "api-sub-1", "status": "ACTIVE", "occurred_at": datetime.now(UTC).isoformat()})
    assert invalid.status_code == 401
    accepted = client.post("/v1/billing/webhooks/test", headers={"X-Billing-Webhook-Token": "test-secret"}, json={"event_id": "api-evt-1", "provider_subscription_id": "api-sub-1", "status": "ACTIVE", "occurred_at": datetime.now(UTC).isoformat()})
    assert accepted.status_code == 200
    replay = client.post("/v1/billing/webhooks/test", headers={"X-Billing-Webhook-Token": "test-secret"}, json={"event_id": "api-evt-1", "provider_subscription_id": "api-sub-1", "status": "ACTIVE", "occurred_at": datetime.now(UTC).isoformat()})
    assert replay.status_code == 200
    assert replay.json()["duplicate"] is True
