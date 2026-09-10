from datetime import datetime, timezone

from app.core.companion_observability import BoundedCompanionTelemetrySink, CompanionTelemetryEvent
from app.core.companion_telemetry_composition import compose_companion_telemetry


def test_composition_preserves_single_local_sink_without_fanout() -> None:
    local = BoundedCompanionTelemetrySink()
    sink = compose_companion_telemetry(local)
    assert sink is local


def test_composition_delivers_to_local_and_persistent_sinks() -> None:
    local = BoundedCompanionTelemetrySink()
    persistent = BoundedCompanionTelemetrySink()
    sink = compose_companion_telemetry(local, persistent)

    event = CompanionTelemetryEvent.create(
        "companion.runtime.started", datetime(2026, 9, 10, tzinfo=timezone.utc)
    )
    sink.record(event)

    assert local.snapshot() == (event,)
    assert persistent.snapshot() == (event,)
