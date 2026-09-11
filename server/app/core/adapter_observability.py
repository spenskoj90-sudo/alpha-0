from __future__ import annotations

from .companion_observability import CompanionTelemetryEvent, CompanionTelemetrySink
from .game_adapter import AdapterEvent


def record_adapter_event(
    sink: CompanionTelemetrySink,
    event: AdapterEvent,
) -> None:
    """Record bounded adapter metadata without copying the raw event payload."""

    adapter_id = event.source.get("adapter_id", "unknown")
    game_id = event.source.get("game_id", "unknown")
    sink.record(
        CompanionTelemetryEvent.create(
            "adapter.event.normalized",
            event.occurred_at,
            attributes={
                "adapter_id": adapter_id,
                "game_id": game_id,
                "event_type": event.event_type,
                "sequence": event.sequence,
                "data_quality": event.data_quality.value,
            },
        )
    )
