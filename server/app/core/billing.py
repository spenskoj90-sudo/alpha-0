"""Provider-neutral billing and entitlement lifecycle primitives.

The core models billing intent, cryptographically verified provider events and
server-derived feature grants. It never embeds production provider credentials.
The legacy shared-token webhook is deliberately restricted to internal/test
providers and cannot activate an external provider subscription.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.billing_provider import (
    BillingProviderAdapter,
    VerifiedBillingWebhook,
)
from app.core.p1_runtime import BillingRuntime, BillingState


@dataclass(frozen=True)
class ProductPlan:
    code: str
    name: str
    currency: str
    amount_minor: int
    interval_days: int
    entitlement_codes: tuple[str, ...]


PLAN_CATALOG: tuple[ProductPlan, ...] = (
    ProductPlan("core", "SENTINEL Core", "EUR", 0, 30, ("core",)),
    ProductPlan("core-plus", "SENTINEL Core Plus", "EUR", 999, 30, ("core", "companion")),
)

PLANS_BY_CODE = {plan.code: plan for plan in PLAN_CATALOG}
LEGACY_INTERNAL_WEBHOOK_PROVIDERS = frozenset({"manual", "test"})


@dataclass(frozen=True)
class BillingWebhookEvent:
    event_id: str
    provider: str
    provider_subscription_id: str
    target_state: BillingState
    occurred_at: datetime
    external_reference: str | None = None
    payload: dict[str, Any] | None = None


class BillingService:
    """Validate plans, provider evidence and lifecycle transitions."""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.runtime = BillingRuntime()

    @staticmethod
    def plans() -> list[dict[str, Any]]:
        return [
            {
                "code": plan.code,
                "name": plan.name,
                "currency": plan.currency,
                "amount_minor": plan.amount_minor,
                "interval_days": plan.interval_days,
                "entitlement_codes": list(plan.entitlement_codes),
            }
            for plan in PLAN_CATALOG
        ]

    def create_subscription(
        self,
        user_id: str,
        plan_code: str,
        *,
        provider: str = "manual",
        provider_subscription_id: str | None = None,
    ) -> dict[str, Any]:
        plan = PLANS_BY_CODE.get(plan_code)
        if plan is None:
            raise ValueError("UNKNOWN_PLAN")
        if not provider or len(provider) > 64:
            raise ValueError("INVALID_PROVIDER")
        return self.store.create_subscription(
            {
                "user_id": user_id,
                "plan_code": plan.code,
                "currency": plan.currency,
                "provider": provider,
                "provider_subscription_id": provider_subscription_id,
                "status": BillingState.PENDING.value,
                "started_at": datetime.now(UTC),
                "expires_at": None,
            }
        )

    def apply_webhook(self, event: BillingWebhookEvent) -> dict[str, Any]:
        """Apply the legacy internal/test webhook boundary only.

        External provider identifiers must use ``apply_verified_webhook`` after
        a BillingProviderAdapter has authenticated the exact raw provider body.
        """

        if event.provider not in LEGACY_INTERNAL_WEBHOOK_PROVIDERS:
            raise ValueError("UNVERIFIED_PROVIDER_EVENT")
        return self._apply_event(event)

    def apply_verified_webhook(self, verified: VerifiedBillingWebhook) -> dict[str, Any]:
        if verified.verification_method not in {"hmac-sha256-v1", "provider-reconciliation"}:
            raise ValueError("UNSUPPORTED_PROVIDER_VERIFICATION")
        event = BillingWebhookEvent(
            event_id=verified.event_id,
            provider=verified.provider,
            provider_subscription_id=verified.provider_subscription_id,
            target_state=verified.target_state,
            occurred_at=verified.occurred_at,
            external_reference=verified.external_reference,
            payload=dict(verified.payload),
        )
        result = self._apply_event(event)
        result["verification_method"] = verified.verification_method
        result["verified_at"] = verified.verified_at
        return result

    def reconcile_provider(
        self,
        adapter: BillingProviderAdapter,
        provider_subscription_id: str,
    ) -> dict[str, Any]:
        """Reconcile one durable subscription against a provider snapshot.

        The adapter owns provider-specific I/O. The resulting lifecycle event ID
        is derived from provider + subscription + provider revision + state, so
        replaying the same snapshot is idempotent.
        """

        snapshot = adapter.read_subscription(provider_subscription_id)
        if snapshot.target_state is BillingState.PENDING:
            raise ValueError("INVALID_WEBHOOK_STATE")
        verified = VerifiedBillingWebhook(
            event_id=snapshot.reconciliation_event_id(),
            provider=snapshot.provider,
            provider_subscription_id=snapshot.provider_subscription_id,
            target_state=snapshot.target_state,
            occurred_at=snapshot.observed_at,
            external_reference=snapshot.external_reference,
            payload=dict(snapshot.payload or {}),
            verification_method="provider-reconciliation",
            verified_at=datetime.now(UTC),
        )
        return self.apply_verified_webhook(verified)

    def feature_entitlements(self, user_id: str) -> tuple[str, ...]:
        """Derive feature grants from ACTIVE subscriptions only.

        Client payloads and presentation metadata are intentionally ignored.
        PENDING, PAST_DUE, CANCELED and EXPIRED subscriptions grant nothing.
        """

        granted: set[str] = set()
        for subscription in self.store.list_subscriptions(user_id):
            if str(subscription.get("status")) != BillingState.ACTIVE.value:
                continue
            plan = PLANS_BY_CODE.get(str(subscription.get("plan_code")))
            if plan is None:
                continue
            granted.update(plan.entitlement_codes)
        return tuple(sorted(granted))

    def has_feature(self, user_id: str, feature_code: str) -> bool:
        if not feature_code or len(feature_code) > 128:
            return False
        return feature_code in self.feature_entitlements(user_id)

    def _apply_event(self, event: BillingWebhookEvent) -> dict[str, Any]:
        if not event.event_id or not event.provider or not event.provider_subscription_id:
            raise ValueError("INVALID_WEBHOOK")
        if event.target_state is BillingState.PENDING:
            raise ValueError("INVALID_WEBHOOK_STATE")
        if event.occurred_at.tzinfo is None:
            raise ValueError("INVALID_WEBHOOK_TIME")
        subscription = self.store.find_subscription_by_provider_id(
            event.provider, event.provider_subscription_id
        )
        if subscription is None:
            raise ValueError("SUBSCRIPTION_NOT_FOUND")
        previous = BillingState(str(subscription["status"]))
        # Duplicate provider deliveries are acknowledged without writing twice.
        if self.store.has_billing_event(event.event_id):
            return {"accepted": False, "duplicate": True, "subscription": subscription}
        transition = (
            self.runtime.transition(
                subscription["id"],
                event.target_state,
                provider=event.provider,
                external_reference=event.external_reference,
            )
            if previous is BillingState.PENDING
            else self._transition_from_persisted(previous, event, subscription)
        )
        updated = self.store.apply_subscription_transition(
            subscription["id"],
            event,
            transition.previous.value,
            transition.current.value,
        )
        self.store.record_billing_event(event, subscription["id"])
        return {"accepted": True, "duplicate": False, "subscription": updated}

    def _transition_from_persisted(
        self,
        previous: BillingState,
        event: BillingWebhookEvent,
        subscription: dict[str, Any],
    ):
        self.runtime.seed(subscription["id"], previous)
        return self.runtime.transition(
            subscription["id"],
            event.target_state,
            provider=event.provider,
            external_reference=event.external_reference,
        )
