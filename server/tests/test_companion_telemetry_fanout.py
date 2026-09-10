from datetime import datetime, timezone

import pytest

from app.core.companion_observability import BoundedCompanionTelemetrySink, CompanionTelemetryEvent
from app.core.companion_telemetry_fanout import FanoutCompanionTelemetrySink


def test_fanout_delivers_same_event_to_all_sinks() -> None:
    first = BoundedCompanionTelemetrySink()
    second = BoundedCompanionTelemetrySink()
    fanout = FanoutCompanionTelemetrySink((first, second))
    event = CompanionTelemetryEvent.create(
        "companion.runtime.started",
        datetime(2026, 9, 10, tzinfo=timezone.utc),
    )

    fanout.record(event)

    assert fanout.sink_count == 2
    assert first.snapshot() == (event,)
    assert second.snapshot() == (event,)


def test_empty_fanout_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one telemetry sink"):
        FanoutCompanionTelemetrySink(())