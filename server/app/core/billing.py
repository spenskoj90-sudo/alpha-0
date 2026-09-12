"""Provider-neutral billing and entitlement lifecycle primitives.

The core deliberately models billing intent and verified provider events, but
never contacts a payment provider or stores provider secrets.  A subscription
is useful to the rest of the product only after the server has accepted an
explicit lifecycle transition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
    """Validate plans and lifecycle transitions before persisting them."""

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
        if not event.event_id or not event.provider or not event.provider_subscription_id:
            raise ValueError("INVALID_WEBHOOK")
        if event.target_state is BillingState.PENDING:
            raise ValueError("INVALID_WEBHOOK_STATE")
        subscription = self.store.find_subscription_by_provider_id(
            event.provider, event.provider_subscription_id
        )
        if subscription is None:
            raise ValueError("SUBSCRIPTION_NOT_FOUND")
        previous = BillingState(str(subscription["status"]))
        # Duplicate provider deliveries are acknowledged without writing twice.
        if self.store.has_billing_event(event.event_id):
            return {"accepted": False, "duplicate": True, "subscription": subscription}
        transition = self.runtime.transition(
            subscription["id"],
            event.target_state,
            provider=event.provider,
            external_reference=event.external_reference,
        ) if previous is BillingState.PENDING else self._transition_from_persisted(previous, event, subscription)
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
