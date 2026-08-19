from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any


class BillingState(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


_ALLOWED_BILLING_TRANSITIONS = {
    BillingState.PENDING: {BillingState.ACTIVE, BillingState.CANCELED},
    BillingState.ACTIVE: {BillingState.PAST_DUE, BillingState.CANCELED, BillingState.EXPIRED},
    BillingState.PAST_DUE: {BillingState.ACTIVE, BillingState.CANCELED, BillingState.EXPIRED},
    BillingState.CANCELED: set(),
    BillingState.EXPIRED: set(),
}


@dataclass(frozen=True)
class BillingTransition:
    subscription_id: str
    previous: BillingState
    current: BillingState
    occurred_at: datetime
    provider: str
    external_reference: str | None = None


class BillingRuntime:
    """Provider-neutral billing state machine; live Stripe credentials are deliberately out of scope."""

    def __init__(self) -> None:
        self._state: dict[str, BillingState] = {}
        self._history: list[BillingTransition] = []
        self._lock = Lock()

    def state(self, subscription_id: str) -> BillingState | None:
        with self._lock:
            return self._state.get(subscription_id)

    def transition(
        self,
        subscription_id: str,
        target: BillingState,
        *,
        provider: str,
        external_reference: str | None = None,
    ) -> BillingTransition:
        with self._lock:
            previous = self._state.get(subscription_id, BillingState.PENDING)
            if target not in _ALLOWED_BILLING_TRANSITIONS[previous]:
                raise ValueError(f"INVALID_BILLING_TRANSITION:{previous}->{target}")
            transition = BillingTransition(subscription_id, previous, target, datetime.now(UTC), provider, external_reference)
            self._state[subscription_id] = target
            self._history.append(transition)
            return transition

    def history(self, subscription_id: str) -> list[BillingTransition]:
        with self._lock:
            return [item for item in self._history if item.subscription_id == subscription_id]


@dataclass(frozen=True)
class EntitlementDecision:
    allowed: bool
    reason: str


class EntitlementEngine:
    """Deterministic server-side entitlement decision engine."""

    def check(self, entitlement: dict[str, Any] | None, *, now: datetime | None = None) -> EntitlementDecision:
        if entitlement is None:
            return EntitlementDecision(False, "ENTITLEMENT_NOT_FOUND")
        current = now or datetime.now(UTC)
        status = str(entitlement.get("status"))
        valid_from = entitlement["valid_from"]
        valid_until = entitlement["valid_until"]
        if status != "ACTIVE":
            return EntitlementDecision(False, f"ENTITLEMENT_{status}")
        if valid_from > current:
            return EntitlementDecision(False, "ENTITLEMENT_NOT_YET_VALID")
        if valid_until < current:
            return EntitlementDecision(False, "ENTITLEMENT_EXPIRED")
        return EntitlementDecision(True, "ENTITLEMENT_ACTIVE")


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class OutboxEvent:
    event_id: str
    kind: str
    payload: dict[str, Any]
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    available_at: float = 0.0
    locked_until: float | None = None


class OutboxManager:
    """Deterministic state machine mirroring the PostgreSQL outbox contract."""

    def __init__(self) -> None:
        self.events: dict[str, OutboxEvent] = {}
        self._lock = Lock()

    def enqueue(self, event: OutboxEvent) -> None:
        with self._lock:
            if event.event_id in self.events:
                raise ValueError("OUTBOX_DUPLICATE")
            self.events[event.event_id] = event

    def claim(self, event_id: str) -> OutboxEvent:
        with self._lock:
            event = self.events[event_id]
            if event.status is not OutboxStatus.PENDING:
                raise ValueError("OUTBOX_NOT_CLAIMABLE")
            event.status = OutboxStatus.PROCESSING
            event.attempts += 1
            return event

    def complete(self, event_id: str) -> None:
        with self._lock:
            event = self.events[event_id]
            if event.status is not OutboxStatus.PROCESSING:
                raise ValueError("OUTBOX_NOT_PROCESSING")
            event.status = OutboxStatus.DONE
            event.locked_until = None

    def fail(self, event_id: str, *, retry: bool) -> None:
        with self._lock:
            event = self.events[event_id]
            if event.status is not OutboxStatus.PROCESSING:
                raise ValueError("OUTBOX_NOT_PROCESSING")
            event.status = OutboxStatus.PENDING if retry else OutboxStatus.FAILED
            event.locked_until = None


class WorkerManager:
    """Worker lifecycle wrapper with explicit failure/retry semantics."""

    def __init__(self, outbox: OutboxManager) -> None:
        self.outbox = outbox

    def process_once(self, event_id: str, handler) -> OutboxStatus:
        event = self.outbox.claim(event_id)
        try:
            handler(event)
        except Exception:
            self.outbox.fail(event_id, retry=True)
            return OutboxStatus.PENDING
        self.outbox.complete(event_id)
        return OutboxStatus.DONE
