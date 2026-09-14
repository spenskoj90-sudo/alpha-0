from __future__ import annotations

from dataclasses import dataclass

from .operational_observability import BoundedOperationalRegistry, normalize_request_id


@dataclass(frozen=True, slots=True)
class FailureInjectionEvidence:
    case: str
    passed: bool
    observed: str

    def as_dict(self) -> dict[str, object]:
        return {"case": self.case, "passed": self.passed, "observed": self.observed}


def run_operational_failure_matrix() -> tuple[FailureInjectionEvidence, ...]:
    """Exercise local fail-closed observability/resource behavior without live dependencies."""
    invalid = normalize_request_id("bad request id with spaces\n")
    correlation_safe = invalid != "bad request id with spaces\n" and len(invalid) == 36

    series = BoundedOperationalRegistry(max_series=2, latency_window=2, max_traces=2)
    for index in range(8):
        series.record(component="failure-test", operation=f"operation-{index}", outcome="ok")
    series_snapshot = series.snapshot()["capacity"]
    series_bounded = series_snapshot["series_used"] == 2 and series_snapshot["series_overflow_events"] == 6

    traces = BoundedOperationalRegistry(max_series=1, latency_window=2, max_traces=2)
    for index in range(5):
        traces.record(
            component="failure-test",
            operation="trace-ring",
            outcome="ok",
            elapsed_ms=float(index),
            trace_id=f"{index:032x}",
            request_id=f"request-{index}",
        )
    trace_snapshot = traces.snapshot()
    trace_bounded = (
        trace_snapshot["capacity"]["traces_used"] == 2
        and trace_snapshot["capacity"]["dropped_traces"] == 3
        and [item["request_id"] for item in trace_snapshot["recent_traces"]] == ["request-3", "request-4"]
    )

    metrics = traces.render_openmetrics()
    identifiers_not_labels = "request-4" not in metrics and f"{4:032x}" not in metrics

    return (
        FailureInjectionEvidence("invalid-correlation-id", correlation_safe, invalid),
        FailureInjectionEvidence("series-cardinality-saturation", series_bounded, str(series_snapshot)),
        FailureInjectionEvidence("bounded-trace-overflow", trace_bounded, str(trace_snapshot["capacity"])),
        FailureInjectionEvidence("identifier-label-isolation", identifiers_not_labels, "bounded identifiers omitted from metrics labels"),
    )
