from __future__ import annotations

import re
import secrets
import uuid
from collections import deque
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from threading import Lock
from time import perf_counter
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Header, Request, Response

from .admin import require_admin

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_LABEL_PATTERN = re.compile(r"[^A-Za-z0-9_./:{}* -]+")
_REQUEST_ID: ContextVar[str | None] = ContextVar("sentinel_request_id", default=None)
_TRACE_ID: ContextVar[str | None] = ContextVar("sentinel_trace_id", default=None)


def normalize_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def new_trace_id() -> str:
    return secrets.token_hex(16)


def current_request_id() -> str | None:
    return _REQUEST_ID.get()


def current_trace_id() -> str | None:
    return _TRACE_ID.get()


def _bounded_label(value: str, *, maximum: int = 160) -> str:
    cleaned = _LABEL_PATTERN.sub("_", value.strip())[:maximum]
    return cleaned or "unknown"


def _nearest_rank(values: tuple[float, ...], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(percentile * len(ordered)) - 1))
    return round(ordered[index], 3)


@dataclass(slots=True)
class _Series:
    count: int
    latencies_ms: deque[float]


@dataclass(frozen=True, slots=True)
class OperationalTrace:
    trace_id: str
    request_id: str | None
    component: str
    operation: str
    outcome: str
    elapsed_ms: float | None
    observed_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "component": self.component,
            "operation": self.operation,
            "outcome": self.outcome,
            "elapsed_ms": self.elapsed_ms,
            "observed_at": self.observed_at.isoformat(),
        }


class BoundedOperationalRegistry:
    """Process-local bounded operational metrics and trace registry.

    Only low-cardinality operational labels are retained. Request/trace ids exist
    only in the bounded recent-trace ring and never become metric labels.
    """

    def __init__(self, *, max_series: int = 128, latency_window: int = 128, max_traces: int = 256) -> None:
        if max_series <= 0 or latency_window <= 0 or max_traces <= 0:
            raise ValueError("operational registry bounds must be positive")
        self.max_series = max_series
        self.latency_window = latency_window
        self.max_traces = max_traces
        self._series: dict[tuple[str, str, str], _Series] = {}
        self._traces: deque[OperationalTrace] = deque(maxlen=max_traces)
        self._series_overflow = 0
        self._trace_dropped = 0
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._series.clear()
            self._traces.clear()
            self._series_overflow = 0
            self._trace_dropped = 0

    def record(
        self,
        *,
        component: str,
        operation: str,
        outcome: str,
        elapsed_ms: float | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
    ) -> None:
        component = _bounded_label(component, maximum=64)
        operation = _bounded_label(operation)
        outcome = _bounded_label(outcome, maximum=64)
        if elapsed_ms is not None:
            elapsed_ms = max(0.0, min(float(elapsed_ms), 86_400_000.0))
        key = (component, operation, outcome)
        with self._lock:
            series = self._series.get(key)
            if series is None:
                if len(self._series) >= self.max_series:
                    self._series_overflow += 1
                else:
                    series = _Series(count=0, latencies_ms=deque(maxlen=self.latency_window))
                    self._series[key] = series
            if series is not None:
                series.count += 1
                if elapsed_ms is not None:
                    series.latencies_ms.append(elapsed_ms)
            if trace_id:
                if len(self._traces) == self.max_traces:
                    self._trace_dropped += 1
                self._traces.append(
                    OperationalTrace(
                        trace_id=trace_id[:32],
                        request_id=request_id[:128] if request_id else None,
                        component=component,
                        operation=operation,
                        outcome=outcome,
                        elapsed_ms=round(elapsed_ms, 3) if elapsed_ms is not None else None,
                        observed_at=datetime.now(UTC),
                    )
                )

    def record_http(self, *, method: str, route: str, status_code: int, elapsed_ms: float, trace_id: str, request_id: str) -> None:
        status_class = f"{max(0, min(9, int(status_code) // 100))}xx"
        self.record(
            component="http",
            operation=f"{method.upper()[:16]} {_bounded_label(route)}",
            outcome=status_class,
            elapsed_ms=elapsed_ms,
            trace_id=trace_id,
            request_id=request_id,
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            series_snapshot = []
            for (component, operation, outcome), series in sorted(self._series.items()):
                values = tuple(series.latencies_ms)
                series_snapshot.append(
                    {
                        "component": component,
                        "operation": operation,
                        "outcome": outcome,
                        "count": series.count,
                        "latency_count": len(values),
                        "p50_ms": _nearest_rank(values, 0.50),
                        "p95_ms": _nearest_rank(values, 0.95),
                        "max_ms": round(max(values), 3) if values else None,
                    }
                )
            traces = [trace.as_dict() for trace in self._traces]
            return {
                "generated_at": datetime.now(UTC).isoformat(),
                "series": series_snapshot,
                "recent_traces": traces,
                "capacity": {
                    "max_series": self.max_series,
                    "series_used": len(self._series),
                    "series_overflow_events": self._series_overflow,
                    "latency_window": self.latency_window,
                    "max_traces": self.max_traces,
                    "traces_used": len(self._traces),
                    "dropped_traces": self._trace_dropped,
                },
            }

    def render_openmetrics(self) -> str:
        snapshot = self.snapshot()
        lines = [
            "# HELP sentinel_operational_events_total Bounded operational event count.",
            "# TYPE sentinel_operational_events_total counter",
        ]
        for item in snapshot["series"]:
            labels = _metrics_labels(item["component"], item["operation"], item["outcome"])
            lines.append(f"sentinel_operational_events_total{{{labels}}} {item['count']}")
            if item["p95_ms"] is not None:
                lines.append(f"sentinel_operational_latency_ms_p95{{{labels}}} {item['p95_ms']}")
                lines.append(f"sentinel_operational_latency_ms_max{{{labels}}} {item['max_ms']}")
        capacity = snapshot["capacity"]
        lines.append(f"sentinel_operational_series_overflow_total {capacity['series_overflow_events']}")
        lines.append(f"sentinel_operational_trace_dropped_total {capacity['dropped_traces']}")
        return "\n".join(lines) + "\n"


def _metrics_labels(component: str, operation: str, outcome: str) -> str:
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    return f'component="{escape(component)}",operation="{escape(operation)}",outcome="{escape(outcome)}"'


def _raw_header(scope: dict[str, Any], name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            try:
                return value.decode("latin-1")
            except UnicodeDecodeError:
                return None
    return None


def _replace_raw_header(scope: dict[str, Any], name: bytes, value: str) -> None:
    headers = [(key, item) for key, item in scope.get("headers", []) if key.lower() != name]
    headers.append((name, value.encode("ascii")))
    scope["headers"] = headers


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path else "UNMATCHED"


operational_registry = BoundedOperationalRegistry()


def install_operational_plane(app: FastAPI, *, store: Any, registry: BoundedOperationalRegistry = operational_registry) -> None:
    if getattr(app.state, "sentinel_operational_plane_installed", False):
        return
    app.state.sentinel_operational_plane_installed = True
    app.state.operational_registry = registry

    @app.middleware("http")
    async def sentinel_operational_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        supplied = _raw_header(request.scope, b"x-request-id")
        rid = normalize_request_id(supplied)
        trace_id = new_trace_id()
        _replace_raw_header(request.scope, b"x-request-id", rid)
        request.state.sentinel_request_id = rid
        request.state.sentinel_trace_id = trace_id
        request_token = _REQUEST_ID.set(rid)
        trace_token = _TRACE_ID.set(trace_id)
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = rid
            response.headers["X-Sentinel-Trace-ID"] = trace_id
            return response
        finally:
            elapsed_ms = (perf_counter() - started) * 1000.0
            registry.record_http(
                method=request.method,
                route=_route_template(request),
                status_code=status_code,
                elapsed_ms=elapsed_ms,
                trace_id=trace_id,
                request_id=rid,
            )
            _REQUEST_ID.reset(request_token)
            _TRACE_ID.reset(trace_token)

    @app.get("/v1/admin/observability")
    def operational_snapshot(
        request: Request,
        x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
    ) -> dict[str, Any]:
        require_admin(x_sentinel_admin_token, request, store)
        rid = current_request_id()
        store.add_audit(
            {
                "actor_user_id": None,
                "actor_device_id": None,
                "action": "admin:observability:read",
                "resource": "operational-observability",
                "decision": "ALLOW",
                "reason_code": "ADMIN_AUTHORIZED",
                "request_id": rid,
            }
        )
        return registry.snapshot()

    @app.get("/v1/admin/metrics")
    def operational_metrics(
        request: Request,
        x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
    ) -> Response:
        require_admin(x_sentinel_admin_token, request, store)
        return Response(content=registry.render_openmetrics(), media_type="text/plain; version=0.0.4; charset=utf-8")
