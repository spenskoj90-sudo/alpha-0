from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.companion_observability import (
    BoundedCompanionTelemetrySink,
    CompanionTelemetryEvent,
)


T0 = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def test_event_requires_companion_namespace_and_timezone() -> None:
    with pytest.raises(ValueError, match="companion namespace"):
        CompanionTelemetryEvent.create("other.runtime.event", T0)
    with pytest.raises(ValueError, match="timezone-aware"):
        CompanionTelemetryEvent.create("companion.runtime.event", T0.replace(tzinfo=None))


def test_event_attributes_are_canonicalized() -> None:
    event = CompanionTelemetryEvent.create(
        "companion.runtime.event",
        T0,
        {"z": 2, "a": "x"},
    )
    assert event.attributes == (("a", "x"), ("z", 2))


def test_sink_is_bounded_and_clearable() -> None:
    sink = BoundedCompanionTelemetrySink(max_events=2)
    sink.record(CompanionTelemetryEvent.create("companion.runtime.one", T0))
    sink.record(CompanionTelemetryEvent.create("companion.runtime.two", T0 + timedelta(seconds=1)))
    sink.record(CompanionTelemetryEvent.create("companion.runtime.three", T0 + timedelta(seconds=2)))

    assert [event.name for event in sink.snapshot()] == [
        "companion.runtime.two",
        "companion.runtime.three",
    ]
    sink.clear()
    assert sink.snapshot() == ()


def test_sink_rejects_non_positive_capacity() -> None:
    with pytest.raises(ValueError, match="max_events"):
        BoundedCompanionTelemetrySink(max_events=0)
