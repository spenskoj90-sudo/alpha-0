from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Callable, Iterable
from uuid import UUID, uuid4


class KnowledgeKind(StrEnum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    RECOMMENDATION = "RECOMMENDATION"


@dataclass(frozen=True)
class Entitlement:
    key: str
    active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class EntitlementEngine:
    def has(self, entitlement: Entitlement, now: datetime | None = None) -> bool:
        if not entitlement.active:
            return False
        now = now or datetime.now(timezone.utc)
        if entitlement.starts_at and now < entitlement.starts_at:
            return False
        if entitlement.ends_at and now >= entitlement.ends_at:
            return False
        return True

    def effective(self, entitlements: Iterable[Entitlement], now: datetime | None = None) -> frozenset[str]:
        return frozenset(e.key for e in entitlements if self.has(e, now))


class BillingEngine:
    """Provider-neutral billing state machine. Webhooks must be verified before calling apply."""

    VALID_TRANSITIONS = {
        "trialing": {"active", "canceled", "past_due"},
        "active": {"active", "past_due", "canceled", "paused"},
        "past_due": {"active", "canceled"},
        "paused": {"active", "canceled"},
        "canceled": set(),
    }

    def transition(self, current: str, requested: str) -> str:
        if requested == current:
            return current
        if requested not in self.VALID_TRANSITIONS.get(current, set()):
            raise ValueError(f"invalid billing transition: {current}->{requested}")
        return requested


@dataclass(frozen=True)
class KnowledgeItem:
    id: UUID
    kind: KnowledgeKind
    statement: str
    confidence: float
    provenance: tuple[str, ...]
    created_at: datetime
    expires_at: datetime | None = None


class KnowledgeEngine:
    def build(
        self,
        kind: KnowledgeKind,
        statement: str,
        confidence: float,
        provenance: Iterable[str],
        expires_at: datetime | None = None,
    ) -> KnowledgeItem:
        if not statement.strip():
            raise ValueError("statement must not be empty")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be in [0,1]")
        if kind is KnowledgeKind.RECOMMENDATION and confidence < 0.5:
            # Low-confidence recommendations are not useful enough to expose as actions.
            raise ValueError("recommendation confidence below safety threshold")
        return KnowledgeItem(
            id=uuid4(), kind=kind, statement=statement.strip(), confidence=confidence,
            provenance=tuple(provenance), created_at=datetime.now(timezone.utc), expires_at=expires_at,
        )


@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID
    event_type: str
    aggregate_id: UUID
    version: int
    payload: dict


class EventProcessor:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[DomainEvent], None]]] = {}
        self._processed: set[tuple[str, UUID]] = set()

    def register(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def process(self, consumer: str, event: DomainEvent) -> None:
        marker = (consumer, event.event_id)
        if marker in self._processed:
            return
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        self._processed.add(marker)


@dataclass
class WorkerManager:
    processors: list[EventProcessor] = field(default_factory=list)
    max_attempts: int = 5

    def run_once(self, events: Iterable[DomainEvent]) -> int:
        processed = 0
        for event in events:
            for processor in self.processors:
                processor.process("default", event)
            processed += 1
        return processed


@dataclass(frozen=True)
class AuditRecord:
    actor_user_id: UUID | None
    action: str
    resource: str
    decision: str
    request_id: UUID
    created_at: datetime


class AuditSystem:
    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def record(self, actor_user_id: UUID | None, action: str, resource: str, decision: str, request_id: UUID) -> None:
        if decision not in {"ALLOW", "DENY"}:
            raise ValueError("invalid audit decision")
        self.records.append(AuditRecord(actor_user_id, action, resource, decision, request_id, datetime.now(timezone.utc)))
