from __future__ import annotations

import re

import pytest

from app.core.operational_observability import (
    OperationalObservabilityRegistry,
    current_correlation_id,
    enter_correlation,
    exit_correlation,
    normalize_request_id,
    normalize_route_template,
)


def test_request_id_normalization_is_header_safe_and_replaces_untrusted_values() -> None:
    assert normalize_request_id("safe.req-1:abc") == "safe.req-1:abc"
    for unsafe in ("", "space value", "x\r\nInjected: yes", "x" * 129, "/path?secret=x"):
        generated = normalize_request_id(unsafe)
        assert generated != unsafe
        assert re.fullmatch(r"[0-9a-f-]{36}", generated)


def test_correlation_context_is_explicit_and_restored() -> None:
    assert current_correlation_id() is None
    token = enter_correlation("corr-123")
    assert current_correlation_id() == "corr-123"
    exit_correlation(token)
    assert current_correlation_id() is None
    with pytest.raises(ValueError, match="CORRELATION_ID_INVALID"):
        enter_correlation("unsafe value")


def test_route_templates_fail_closed_instead_of_recording_concrete_urls() -> None:
    assert normalize_route_template("/v1/devices/{device_id}") == "/v1/devices/{device_id}"
    assert normalize_route_template("/v1/users/alice@example.com?token=x") == "/_unmatched"
    assert normalize_route_template("not-a-route") == "/_unmatched"


def test_registry_uses_low_cardinality_series_and_bounded_trace_window() -> None:
    registry = OperationalObservabilityRegistry(max_series=16, sample_window=8, max_traces=16)
    for index in range(20):
        registry.record_http(
            route="/v1/devices/{device_id}",
            method="GET",
            status_code=200,
            duration_ms=float(index),
            correlation_id=f"corr-{index}",
        )
    registry.record_dependency(component="voice_stt", outcome="failure", duration_ms=12.5, correlation_id="voice-corr")
    snapshot = registry.snapshot(trace_limit=16)

    http = next(item for item in snapshot["series"] if item["metric"] == "http.server.request")
    assert http["labels"] == {"method": "GET", "route": "/v1/devices/{device_id}", "status_class": "2xx"}
    assert http["count"] == 20
    assert http["sample_count"] == 8
    assert http["p95_ms"] == 19.0
    assert len(snapshot["recent_traces"]) == 16
    assert snapshot["recent_traces"][-1]["operation"] == "dependency.voice_stt"
    assert "audio" not in str(snapshot).lower()
    assert "token" not in str(snapshot).lower()


def test_registry_rejects_arbitrary_dependency_and_outcome_dimensions() -> None:
    registry = OperationalObservabilityRegistry()
    with pytest.raises(ValueError, match="DEPENDENCY_INVALID"):
        registry.record_dependency(component="user-controlled-provider-name", outcome="success", duration_ms=1)
    with pytest.raises(ValueError, match="OUTCOME_INVALID"):
        registry.record_dependency(component="voice_stt", outcome="customer@example.com", duration_ms=1)


def test_registry_caps_series_instead_of_evicting_existing_evidence() -> None:
    registry = OperationalObservabilityRegistry(max_series=16)
    methods = ["GET", "POST", "PUT", "PATCH"]
    statuses = [200, 400, 500, 503]
    for method in methods:
        for status in statuses:
            registry.record_http(route=f"/v1/static/{method.lower()}/{status}", method=method, status_code=status, duration_ms=1, correlation_id="corr")
    # one more distinct series exceeds configured capacity
    registry.record_dependency(component="voice_stt", outcome="success", duration_ms=1)
    snapshot = registry.snapshot()
    assert snapshot["series_count"] == 16
    assert snapshot["dropped_series"] == 1
