from datetime import UTC, datetime, timedelta

import pytest

from app.core.companion_runtime import CompanionRuntime
from app.core.performance_baseline import (
    PerformanceBudget,
    PerformanceSample,
    evaluate_budget,
    measure,
    measure_latency_samples,
    summarize,
)


def test_measure_latency_samples_is_reproducible_from_supplied_timestamps():
    start = datetime(2026, 9, 11, tzinfo=UTC)
    samples = [(start + timedelta(milliseconds=i), start + timedelta(milliseconds=i + latency)) for i, latency in enumerate((10, 20, 30, 40, 50))]
    runtime = CompanionRuntime()
    snapshot = measure_latency_samples(runtime, samples)
    assert snapshot.count == 5
    assert snapshot.minimum_ms == 10.0
    assert snapshot.maximum_ms == 50.0
    assert snapshot.average_ms == 30.0
    assert snapshot.p95_ms == 50.0


def test_measure_returns_result_and_nonnegative_local_sample():
    result, sample = measure("unit", lambda: 42)
    assert result == 42
    assert sample.operation == "unit"
    assert sample.elapsed_ms >= 0


def test_summarize_is_deterministic_for_supplied_samples():
    summary = summarize((PerformanceSample("unit", 2.0), PerformanceSample("unit", 4.0), PerformanceSample("unit", 6.0)))
    assert summary.count == 3
    assert summary.mean_ms == 4.0
    assert summary.median_ms == 4.0
    assert summary.min_ms == 2.0
    assert summary.max_ms == 6.0


def test_summarize_rejects_empty_and_mixed_operations():
    with pytest.raises(ValueError):
        summarize(())
    with pytest.raises(ValueError):
        summarize((PerformanceSample("a", 1), PerformanceSample("b", 2)))


def test_performance_budget_is_measurable_and_operation_scoped():
    assert evaluate_budget(PerformanceSample("unit", 4.0), PerformanceBudget("unit", 4.0)).passed
    assert not evaluate_budget(PerformanceSample("unit", 4.1), PerformanceBudget("unit", 4.0)).passed
    with pytest.raises(ValueError, match="operations"):
        evaluate_budget(PerformanceSample("other", 1), PerformanceBudget("unit", 2))
