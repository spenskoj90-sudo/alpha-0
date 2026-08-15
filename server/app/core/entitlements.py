from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class EntitlementStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


@dataclass(frozen=True)
class Entitlement:
    id: str
    user_id: str
    game_id: str
    source: str
    status: EntitlementStatus
    valid_from: datetime
    valid_until: datetime

    def is_active(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return self.status is EntitlementStatus.ACTIVE and self.valid_from <= current <= self.valid_until
