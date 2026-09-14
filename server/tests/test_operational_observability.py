from __future__ import annotations

import re
import uuid

from fastapi.testclient import TestClient

from app.core.operational_observability import BoundedOperationalRegistry, normalize_request_id, operational_registry
from app.main import app


client = TestClient(app, client=("127.0.0.1", 45555))
admin_client = TestClient(app, client=("198.51.100.44", 45556))


def test_request_id_normalization_accepts_bounded_safe_value_and_replaces_invalid_input() -> None:
    assert normalize_request_id("client.request-1:abc") == "client.request-1:abc"
    replacement = normalize_request_id("bad request id with spaces\nAuthorization: secret")
    uuid.UUID(replacement)
    assert "secret" not in replacement


def test_registry_is_bounded_and_keeps_high_cardinality_ids_out_of_metric_labels() -> None:
    registry = BoundedOperationalRegistry(max_series=2, latency_window=3, max_traces=2)
    for index in range(5):
        registry.record(
            component="http",
            operation=f"GET /bounded/{index}",
            outcome="2xx",
            elapsed_ms=float(index + 1),
            trace_id=f"{index:032x}",
            request_id=f"request-{index}",
        )
    snapshot = registry.snapshot()
    assert snapshot["capacity"]["series_used"] == 2
    assert snapshot["capacity"]["series_overflow_events"] == 3
    assert snapshot["capacity"]["traces_used"] == 2
    assert snapshot["capacity"]["dropped_traces"] == 3
    metrics = registry.render_openmetrics()
    assert "request-4" not in metrics
    assert f"{4:032x}" not in metrics


def test_latency_window_uses_bounded_nearest_rank_percentiles() -> None:
    registry = BoundedOperationalRegistry(max_series=4, latency_window=4, max_traces=4)
    for value in (1.0, 2.0, 3.0, 100.0, 200.0):
        registry.record(component="benchmark", operation="sample", outcome="ok", elapsed_ms=value)
    series = registry.snapshot()["series"][0]
    assert series["latency_count"] == 4
    assert series["p50_ms"] == 3.0
    assert series["p95_ms"] == 200.0
    assert series["max_ms"] == 200.0


def test_global_http_correlation_uses_route_template_and_returns_headers() -> None:
    operational_registry.clear()
    supplied = "client-flow-123"
    response = client.get("/healthz?token=must-not-be-observed", headers={"X-Request-ID": supplied})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == supplied
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-sentinel-trace-id"])
    snapshot = operational_registry.snapshot()
    http_series = [item for item in snapshot["series"] if item["component"] == "http"]
    assert any(item["operation"] == "GET /healthz" and item["outcome"] == "2xx" for item in http_series)
    serialized = str(snapshot)
    assert "must-not-be-observed" not in serialized


def test_invalid_http_request_id_is_replaced_before_endpoint_and_error_handling() -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "invalid request id"})
    assert response.status_code == 200
    uuid.UUID(response.headers["x-request-id"])


def test_admin_observability_and_metrics_are_fail_closed_and_never_expose_admin_token(monkeypatch) -> None:
    operational_registry.clear()
    monkeypatch.setenv("SENTINEL_ADMIN_TOKEN", "admin-observability-secret")
    denied = admin_client.get("/v1/admin/observability")
    assert denied.status_code == 403

    headers = {"X-Sentinel-Admin-Token": "admin-observability-secret", "X-Request-ID": "admin-observe"}
    response = admin_client.get("/v1/admin/observability", headers=headers)
    assert response.status_code == 200
    assert "series" in response.json()
    assert "recent_traces" in response.json()
    assert "admin-observability-secret" not in response.text

    metrics = admin_client.get("/v1/admin/metrics", headers=headers)
    assert metrics.status_code == 200
    assert "sentinel_operational_events_total" in metrics.text
    assert "admin-observability-secret" not in metrics.text
