from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.billing import BillingService, BillingWebhookEvent
from app.core.billing_provider import ProviderSubscriptionSnapshot, VerifiedBillingWebhook
from app.core.p1_runtime import BillingState
from app.core.store import MemoryStore


def _verified(
    *,
    method: str = "hmac-sha256-v1",
    local_id: str | None = None,
    provider_id: str = "sub-provider-1",
    state: BillingState = BillingState.ACTIVE,
    payload=None,
):
    now = datetime.now(UTC)
    return VerifiedBillingWebhook(
        event_id="evt-verified-1",
        provider="signed-test",
        provider_subscription_id=provider_id,
        target_state=state,
        occurred_at=now,
        external_reference="external",
        payload={} if payload is None else payload,
        verification_method=method,
        verified_at=now,
        local_subscription_id=local_id,
    )


@pytest.mark.parametrize("provider", ["", "x" * 65])
def test_subscription_creation_rejects_invalid_provider(provider: str) -> None:
    service = BillingService(MemoryStore())
    with pytest.raises(ValueError, match="INVALID_PROVIDER"):
        service.create_subscription("u1", "core-plus", provider=provider)


def test_plan_catalog_projection_is_stable_and_server_owned() -> None:
    plans = BillingService.plans()
    assert [item["code"] for item in plans] == ["core", "core-plus"]
    assert plans[0]["amount_minor"] == 0
    assert plans[1]["entitlement_codes"] == ["core", "companion"]


@pytest.mark.parametrize("method", ["", "untrusted", "stripe-webhook-v0"])
def test_verified_webhook_rejects_unapproved_verification_methods(method: str) -> None:
    service = BillingService(MemoryStore())
    with pytest.raises(ValueError, match="UNSUPPORTED_PROVIDER_VERIFICATION"):
        service.apply_verified_webhook(_verified(method=method))


def test_verified_webhook_binds_unbound_local_subscription_once() -> None:
    store = MemoryStore()
    service = BillingService(store)
    local = service.create_subscription("u1", "core-plus", provider="signed-test")
    verified = _verified(local_id=local["id"], provider_id="sub-bound-1")

    result = service.apply_verified_webhook(verified)
    assert result["subscription"]["provider_subscription_id"] == "sub-bound-1"
    assert result["subscription"]["status"] == "ACTIVE"


def test_verified_webhook_accepts_matching_existing_binding_and_rejects_redirect() -> None:
    store = MemoryStore()
    service = BillingService(store)
    first = service.create_subscription(
        "u1", "core-plus", provider="signed-test", provider_subscription_id="sub-existing"
    )
    matching = _verified(local_id=first["id"], provider_id="sub-existing")
    assert service.apply_verified_webhook(matching)["subscription"]["id"] == first["id"]

    second = service.create_subscription("u2", "core-plus", provider="signed-test")
    redirect = _verified(
        local_id=second["id"],
        provider_id="sub-existing",
    )
    redirect = VerifiedBillingWebhook(
        **{**redirect.__dict__, "event_id": "evt-redirect"}
    )
    with pytest.raises(ValueError, match="SUBSCRIPTION_BINDING_MISMATCH"):
        service.apply_verified_webhook(redirect)


class SnapshotAdapter:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def read_subscription(self, _provider_subscription_id):
        return self.snapshot


def test_reconciliation_rejects_pending_provider_snapshot() -> None:
    snapshot = ProviderSubscriptionSnapshot(
        provider="signed-test",
        provider_subscription_id="sub-1",
        target_state=BillingState.PENDING,
        observed_at=datetime.now(UTC),
        revision="r1",
    )
    with pytest.raises(ValueError, match="INVALID_WEBHOOK_STATE"):
        BillingService(MemoryStore()).reconcile_provider(SnapshotAdapter(snapshot), "sub-1")


def test_reconciliation_tolerates_absent_optional_payload() -> None:
    store = MemoryStore()
    service = BillingService(store)
    local = service.create_subscription(
        "u1",
        "core-plus",
        provider="signed-test",
        provider_subscription_id="sub-reconcile-none",
    )
    snapshot = ProviderSubscriptionSnapshot(
        provider="signed-test",
        provider_subscription_id="sub-reconcile-none",
        target_state=BillingState.ACTIVE,
        observed_at=datetime.now(UTC),
        revision="r1",
        payload=None,
    )
    result = service.reconcile_provider(SnapshotAdapter(snapshot), "sub-reconcile-none")
    assert result["subscription"]["id"] == local["id"]
    assert result["verification_method"] == "provider-reconciliation"


def test_feature_entitlements_ignore_nonactive_and_unknown_plans() -> None:
    store = MemoryStore()
    service = BillingService(store)
    active = service.create_subscription("u1", "core-plus", provider="test", provider_subscription_id="sub-active")
    inactive = service.create_subscription("u1", "core", provider="test", provider_subscription_id="sub-pending")
    service.apply_webhook(
        BillingWebhookEvent(
            "evt-active",
            "test",
            "sub-active",
            BillingState.ACTIVE,
            datetime.now(UTC),
        )
    )
    # Corrupt only the plan code of a second active-like record to prove unknown
    # persisted plans cannot manufacture grants.
    store.subscriptions[inactive["id"]]["status"] = "ACTIVE"
    store.subscriptions[inactive["id"]]["plan_code"] = "removed-plan"

    assert service.feature_entitlements("u1") == ("companion", "core")
    assert service.feature_entitlements("missing") == ()
    assert service.has_feature("u1", "companion") is True
    assert service.has_feature("u1", "missing") is False
    assert service.has_feature("u1", "") is False
    assert service.has_feature("u1", "x" * 129) is False


@pytest.mark.parametrize(
    ("event", "error"),
    [
        (
            BillingWebhookEvent("", "test", "sub", BillingState.ACTIVE, datetime.now(UTC)),
            "INVALID_WEBHOOK",
        ),
        (
            BillingWebhookEvent("evt", "", "sub", BillingState.ACTIVE, datetime.now(UTC)),
            "INVALID_WEBHOOK",
        ),
        (
            BillingWebhookEvent("evt", "test", "", BillingState.ACTIVE, datetime.now(UTC)),
            "INVALID_WEBHOOK",
        ),
        (
            BillingWebhookEvent("evt", "test", "sub", BillingState.PENDING, datetime.now(UTC)),
            "INVALID_WEBHOOK_STATE",
        ),
        (
            BillingWebhookEvent("evt", "test", "sub", BillingState.ACTIVE, datetime.now()),
            "INVALID_WEBHOOK_TIME",
        ),
        (
            BillingWebhookEvent("evt", "test", "missing", BillingState.ACTIVE, datetime.now(UTC)),
            "SUBSCRIPTION_NOT_FOUND",
        ),
    ],
)
def test_event_application_rejects_invalid_identity_state_time_and_binding(event, error: str) -> None:
    service = BillingService(MemoryStore())
    with pytest.raises(ValueError, match=error):
        service.apply_webhook(event)


def test_persisted_nonpending_state_uses_seeded_transition_path() -> None:
    store = MemoryStore()
    service = BillingService(store)
    local = service.create_subscription(
        "u1", "core-plus", provider="test", provider_subscription_id="sub-seeded"
    )
    now = datetime.now(UTC)
    service.apply_webhook(
        BillingWebhookEvent("evt-activate", "test", "sub-seeded", BillingState.ACTIVE, now)
    )
    changed = service.apply_webhook(
        BillingWebhookEvent("evt-past-due", "test", "sub-seeded", BillingState.PAST_DUE, now)
    )
    assert changed["subscription"]["id"] == local["id"]
    assert changed["subscription"]["status"] == "PAST_DUE"
