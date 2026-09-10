import pytest

from app.core.companion_latency_stats import CompanionLatencyStats


def test_snapshot_is_empty_before_observations() -> None:
    assert CompanionLatencyStats().snapshot() == (
        CompanionLatencyStats().snapshot()
    )


def test_snapshot_reports_bounded_statistics() -> None:
    stats = CompanionLatencyStats(max_samples=3)
    for value in (10.0, 20.0, 30.0, 40.0):
        stats.observe(value)

    snapshot = stats.snapshot()

    assert snapshot.count == 3
    assert snapshot.minimum_ms == 20.0
    assert snapshot.maximum_ms == 40.0
    assert snapshot.average_ms == 30.0
    assert snapshot.p95_ms == 40.0


def test_negative_latency_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        CompanionLatencyStats().observe(-1.0)


def test_clear_removes_retained_samples() -> None:
    stats = CompanionLatencyStats()
    stats.observe(12.0)
    stats.clear()

    assert stats.snapshot().count == 0
