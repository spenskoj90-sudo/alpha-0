from __future__ import annotations

from app.core.operational_resilience import run_operational_failure_matrix


def test_operational_failure_injection_matrix_is_deterministic_and_passes_fail_closed_cases() -> None:
    evidence = run_operational_failure_matrix()
    assert {item.case for item in evidence} == {
        "invalid-correlation-id",
        "series-cardinality-saturation",
        "bounded-trace-overflow",
        "identifier-label-isolation",
    }
    assert all(item.passed for item in evidence)
