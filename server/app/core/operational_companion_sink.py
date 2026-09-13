from __future__ import annotations

from .companion_observability import CompanionTelemetryEvent
from .operational_observability import OperationalObservabilityRegistry, observability_registry


def _outcome_for_event(name: str) -> str:
    lowered = name.lower()
    if any(part in lowered for part in ("denied", "failed", "failure", "error")):
        return "failure"
    if any(part in lowered for part in ("degraded", "backpressure", "dropped")):
        return "degraded"
    if any(part in lowered for part in ("disconnect", "closed", "stopped")):
        return "disconnect"
    return "success"


def _duration_for_event(event: CompanionTelemetryEvent) -> float:
    # Only explicitly named bounded operational latency fields are considered.
    # All other telemetry attributes are deliberately ignored by this adapter.
    for key, value in event.attributes:
        if key in {"latency_ms", "rtt_ms", "elapsed_ms"} and isinstance(value, (int, float)):
            numeric = float(value)
            if 0 <= numeric <= 300_000:
                return numeric
    return 0.0


class OperationalCompanionTelemetrySink:
    """Bridge Companion operational events into low-cardinality operator metrics."""

    def __init__(self, registry: OperationalObservabilityRegistry = observability_registry) -> None:
        self.registry = registry

    def record(self, event: CompanionTelemetryEvent) -> None:
        self.registry.record_companion_event(
            event=event.name,
            outcome=_outcome_for_event(event.name),
            duration_ms=_duration_for_event(event),
        )
