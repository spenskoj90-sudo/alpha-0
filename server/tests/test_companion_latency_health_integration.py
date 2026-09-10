from datetime import datetime, timedelta, timezone

from app.core.companion_latency_stats import CompanionLatencyStats
from app.core.companion_runtime import CompanionRuntime


T0 = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def test_runtime_records_latency_into_bounded_statistics() -> None:
    stats = CompanionLatencyStats(max_samples=3)
    runtime = CompanionRuntime(latency_stats=stats)

    runtime.observe_latency(T0, T0 + timedelta(milliseconds=10))
    runtime.observe_latency(T0, T0 + timedelta(milliseconds=20))
    runtime.observe_latency(T0, T0 + timedelta(milliseconds=30))
    runtime.observe_latency(T0, T0 + timedelta(milliseconds=40))

    snapshot = stats.snapshot()
    assert snapshot.count == 3
    assert snapshot.minimum_ms == 20.0
    assert snapshot.maximum_ms == 40.0
    assert snapshot.average_ms == 30.0
    assert snapshot.p95_ms == 40.0
