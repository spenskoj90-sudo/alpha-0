from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class CompanionTelemetryEvent:
    """Privacy-safe operational event; payload contains no user/game raw data."""

    name: str
    observed_at: datetime
    attributes: tuple[tuple[str, str | int | float | bool], ...] = ()

    def __post_init__(self) -> None:
        if not self.name.startswith("companion."):
            raise ValueError("event name must use the companion namespace")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if tuple(sorted(self.attributes)) != self.attributes:
            raise ValueError("attributes must be sorted")

    @classmethod
    def create(
        cls,
        name: str,
        observed_at: datetime,
        attributes: Mapping[str, str | int | float | bool] | None = None,
    ) -> CompanionTelemetryEvent:
        return cls(
            name=name,
            observed_at=observed_at,
            attributes=tuple(sorted((attributes or {}).items())),
        )


class CompanionTelemetrySink(Protocol):
    def record(self, event: CompanionTelemetryEvent) -> None: ...


class BoundedCompanionTelemetrySink:
    """Thread-safe bounded sink for local/runtime observability.

    It intentionally retains only operational metadata and never performs I/O.
    A later persistent/provider sink can implement the same protocol without
    coupling the Companion runtime to a telemetry vendor.
    """

    def __init__(self, *, max_events: int = 256) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        self._events: deque[CompanionTelemetryEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def record(self, event: CompanionTelemetryEvent) -> None:
        with self._lock:
            self._events.append(event)

    def snapshot(self) -> tuple[CompanionTelemetryEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
