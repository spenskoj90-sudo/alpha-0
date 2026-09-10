from __future__ import annotations

from collections.abc import Iterable

from .companion_observability import CompanionTelemetryEvent, CompanionTelemetrySink


class FanoutCompanionTelemetrySink:
    """Deliver one bounded operational event to multiple independent sinks."""

    def __init__(self, sinks: Iterable[CompanionTelemetrySink]) -> None:
        self._sinks = tuple(sinks)
        if not self._sinks:
            raise ValueError("at least one telemetry sink is required")

    @property
    def sink_count(self) -> int:
        return len(self._sinks)

    def record(self, event: CompanionTelemetryEvent) -> None:
        for sink in self._sinks:
            sink.record(event)
