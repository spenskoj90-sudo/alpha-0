from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import text

from .companion_observability import CompanionTelemetryEvent, CompanionTelemetrySink


class _EngineLike(Protocol):
    def begin(self): ...


class PostgresCompanionTelemetrySink:
    """Persistent Companion telemetry sink with explicit retention semantics.

    The sink persists only the bounded operational event contract. It does not
    perform provider calls, authorize actions, or accept raw game payloads.
    """

    def __init__(self, engine: _EngineLike, *, retention: timedelta = timedelta(days=30)) -> None:
        if retention <= timedelta(0):
            raise ValueError("retention must be positive")
        self._engine = engine
        self.retention = retention

    def record(self, event: CompanionTelemetryEvent) -> None:
        expires_at = event.observed_at.astimezone(timezone.utc) + self.retention
        attributes = dict(event.attributes)
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO companion_telemetry_events
                        (id, event_name, observed_at, attributes_json, expires_at)
                    VALUES
                        (:id, :event_name, :observed_at, CAST(:attributes_json AS JSONB), :expires_at)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "event_name": event.name,
                    "observed_at": event.observed_at.astimezone(timezone.utc),
                    "attributes_json": json.dumps(attributes, sort_keys=True, separators=(",", ":")),
                    "expires_at": expires_at,
                },
            )

    def purge_expired(self, now: datetime | None = None) -> int:
        timestamp = now or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        timestamp = timestamp.astimezone(timezone.utc)
        with self._engine.begin() as connection:
            result = connection.execute(
                text("DELETE FROM companion_telemetry_events WHERE expires_at <= :now"),
                {"now": timestamp},
            )
            return int(result.rowcount or 0)
