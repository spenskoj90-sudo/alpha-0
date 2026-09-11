from datetime import datetime, timedelta, timezone

from app.core.companion_runtime import CompanionRuntime
from app.core.performance_baseline import measure_latency_samples


def test_measure_latency_samples_is_reproducible_from_supplied_timestamps():
    start = datetime(2026, 9, 11, tzinfo=timezone.utc)
    samples = [(start + timedelta(milliseconds=i), start + timedelta(milliseconds=i + latency)) for i, latency in enumerate((10, 20, 30, 40, 50))]
    runtime = CompanionRuntime()
    snapshot = measure_latency_samples(runtime, samples)
    assert snapshot.count == 5
    assert snapshot.minimum_ms == 10.0
    assert snapshot.maximum_ms == 50.0
    assert snapshot.average_ms == 30.0
    assert snapshot.p95_ms == 50.0
