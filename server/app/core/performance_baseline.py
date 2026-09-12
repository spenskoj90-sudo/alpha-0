from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean, median
from time import monotonic
from typing import Callable, TypeVar

from .companion_latency_stats import CompanionLatencySnapshot
from .companion_runtime import CompanionRuntime

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PerformanceSample:
    operation: str
    elapsed_ms: float

    def __post_init__(self) -> None:
        if not self.operation or len(self.operation) > 128:
            raise ValueError("operation must be between 1 and 128 characters")
        if self.elapsed_ms < 0:
            raise ValueError("elapsed_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    operation: str
    count: int
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float


@dataclass(frozen=True, slots=True)
class PerformanceBudget:
    """A measurable local budget; it never implies remote/E2E performance."""

    operation: str
    max_elapsed_ms: float

    def __post_init__(self) -> None:
        if not self.operation or len(self.operation) > 128:
            raise ValueError("operation must be between 1 and 128 characters")
        if self.max_elapsed_ms < 0:
            raise ValueError("max_elapsed_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class PerformanceBudgetResult:
    operation: str
    observed_ms: float
    budget_ms: float
    passed: bool


def evaluate_budget(sample: PerformanceSample, budget: PerformanceBudget) -> PerformanceBudgetResult:
    if sample.operation != budget.operation:
        raise ValueError("sample and budget operations must match")
    return PerformanceBudgetResult(
        operation=sample.operation,
        observed_ms=sample.elapsed_ms,
        budget_ms=budget.max_elapsed_ms,
        passed=sample.elapsed_ms <= budget.max_elapsed_ms,
    )


def measure(operation: str, fn: Callable[[], T]) -> tuple[T, PerformanceSample]:
    """Measure one local callable invocation; no remote/E2E claim is implied."""
    started = monotonic()
    result = fn()
    elapsed_ms = (monotonic() - started) * 1000.0
    return result, PerformanceSample(operation=operation, elapsed_ms=elapsed_ms)


def summarize(samples: list[PerformanceSample] | tuple[PerformanceSample, ...]) -> PerformanceSummary:
    if not samples:
        raise ValueError("at least one performance sample is required")
    operation = samples[0].operation
    if any(sample.operation != operation for sample in samples):
        raise ValueError("all performance samples must use the same operation")
    values = [sample.elapsed_ms for sample in samples]
    return PerformanceSummary(operation, len(values), mean(values), median(values), min(values), max(values))


def measure_latency_samples(
    runtime: CompanionRuntime,
    samples: list[tuple[datetime, datetime]],
) -> CompanionLatencySnapshot:
    """Record supplied timestamps and return reproducible Companion statistics."""
    for sent_at, received_at in samples:
        runtime.observe_latency(sent_at, received_at)
    return runtime.latency_stats.snapshot()
