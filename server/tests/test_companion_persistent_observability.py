from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.core.companion_observability import CompanionTelemetryEvent
from app.core.companion_persistent_observability import PostgresCompanionTelemetrySink


T0 = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def test_sink_rejects_non_positive_retention() -> None:
    with pytest.raises(ValueError, match="retention"):
        PostgresCompanionTelemetrySink(MagicMock(), retention=timedelta(0))


def test_sink_persists_canonical_operational_attributes_with_expiry() -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    event = CompanionTelemetryEvent.create(
        "companion.runtime.latency",
        T0,
        {"z": 2, "latency_ms": 12.5, "mode": "ACTIVE"},
    )

    PostgresCompanionTelemetrySink(engine, retention=timedelta(days=7)).record(event)

    connection.execute.assert_called_once()
    params = connection.execute.call_args.args[1]
    assert params["event_name"] == "companion.runtime.latency"
    assert params["observed_at"] == T0
    assert params["expires_at"] == T0 + timedelta(days=7)
    assert params["attributes_json"] == '{"latency_ms":12.5,"mode":"ACTIVE","z":2}'


def test_sink_purges_expired_rows_and_normalizes_timezone() -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.rowcount = 3
    local_now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone(timedelta(hours=3)))

    deleted = PostgresCompanionTelemetrySink(engine).purge_expired(local_now)

    assert deleted == 3
    params = connection.execute.call_args.args[1]
    assert params["now"] == datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
