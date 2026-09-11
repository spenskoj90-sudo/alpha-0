from datetime import datetime, timezone

from app.core.adapter_observability import record_adapter_event
from app.core.companion_observability import BoundedCompanionTelemetrySink
from app.core.game_adapter import AdapterEvent, DataQuality


def test_adapter_observability_records_metadata_without_raw_payload():
    sink = BoundedCompanionTelemetrySink()
    event = AdapterEvent(
        event_id="evt-1",
        schema_version="1.0",
        occurred_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        sequence=7,
        source={"adapter_id": "wow-conservative", "game_id": "world-of-warcraft"},
        event_type="wow.passive_observation",
        payload={"character_name": "should-not-be-recorded"},
        data_quality=DataQuality.MEDIUM,
        provenance=["wow-conservative"],
    )

    record_adapter_event(sink, event)

    recorded = sink.snapshot()
    assert len(recorded) == 1
    assert recorded[0].name == "adapter.event.normalized"
    assert recorded[0].attributes == (
        ("adapter_id", "wow-conservative"),
        ("data_quality", "MEDIUM"),
        ("event_type", "wow.passive_observation"),
        ("game_id", "world-of-warcraft"),
        ("sequence", 7),
    )
    assert "character_name" not in str(recorded[0].attributes)
