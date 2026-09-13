from __future__ import annotations

import math
import re
import uuid
from collections import deque
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Iterable

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ROUTE_PATTERN = re.compile(r"^/[A-Za-z0-9_./{}:-]{0,159}$")
_EVENT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"})
_ALLOWED_DEPENDENCIES = frozenset({"voice_stt", "voice_tts", "companion_ws", "billing_provider", "postgres"})
_ALLOWED_OUTCOMES = frozenset({"success", "failure", "timeout", "unavailable", "accepted", "rejected", "denied", "degraded", "disconnect"})
_MAX_DURATION_MS = 300_000.0

_current_correlation_id: ContextVar[str | None] = ContextVar("sentinel_correlation_id", default=None)


def normalize_request_id(value: str | None) -> str:
    """Return a bounded header-safe correlation id or a fresh UUID.

    Caller-controlled values are accepted only when they fit the intentionally
    narrow opaque identifier grammar. Invalid values are replaced, never echoed.
    """
    if value and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


def current_correlation_id() -> str | None:
    return _current_correlation_id.get()


def enter_correlation(correlation_id: str) -> Token[str | None]:
    if not _REQUEST_ID_PATTERN.fullmatch(correlation_id):
        raise ValueError("CORRELATION_ID_INVALID")
    return _current_correlation_id.set(correlation_id)


def exit_correlation(token: Token[str | None]) -> None:
    _current_correlation_id.reset(token)


def normalize_route_template(value: str | None) -> str:
    if value and _ROUTE_PATTERN.fullmatch(value):
        return value
    return "/_unmatched"


def _normalize_event(value: str) -> str:
    normalized = value.strip().lower()
    if not _EVENT_PATTERN.fullmatch(normalized):
        raise ValueError("OBSERVABILITY_EVENT_INVALID")
    return normalized


def _bounded_duration(value: float) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError("OBSERVABILITY_DURATION_INVALID")
    return min(numeric, _MAX_DURATION_MS)


def _nearest_rank_p95(values: Iterable[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


@dataclass(frozen=True, slots=True)
class OperationalTrace:
    correlation_id: str
    operation: str
    outcome: str
    duration_ms: float
    observed_at: datetime


class _Series:
    __slots__ = ("count", "total_ms", "min_ms", "max_ms", "samples")

    def __init__(self, sample_window: int) -> None:
        self.count = 0
        self.total_ms = 0.0
        self.min_ms: float | None = None
        self.max_ms: float | None = None
        self.samples: deque[float] = deque(maxlen=sample_window)

    def observe(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = duration_ms if self.min_ms is None else min(self.min_ms, duration_ms)
        self.max_ms = duration_ms if self.max_ms is None else max(self.max_ms, duration_ms)
        self.samples.append(duration_ms)

    def snapshot(self) -> dict[str, int | float]:
        return {
            "count": self.count,
            "average_ms": round(self.total_ms / self.count, 3) if self.count else 0.0,
            "min_ms": round(self.min_ms or 0.0, 3),
            "max_ms": round(self.max_ms or 0.0, 3),
            "p95_ms": round(_nearest_rank_p95(self.samples), 3),
            "sample_count": len(self.samples),
        }


class OperationalObservabilityRegistry:
    """Bounded low-cardinality metrics plus recent privacy-safe traces.

    The public recording methods define every accepted dimension. Arbitrary
    metric names, route instances, user identifiers and provider labels cannot
    create unbounded series.
    """

    def __init__(self, *, max_series: int = 256, sample_window: int = 128, max_traces: int = 256) -> None:
        if not 16 <= max_series <= 2048:
            raise ValueError("OBSERVABILITY_SERIES_LIMIT_INVALID")
        if not 8 <= sample_window <= 1024:
            raise ValueError("OBSERVABILITY_SAMPLE_WINDOW_INVALID")
        if not 16 <= max_traces <= 2048:
            raise ValueError("OBSERVABILITY_TRACE_LIMIT_INVALID")
        self._max_series = max_series
        self._sample_window = sample_window
        self._series: dict[tuple[str, tuple[tuple[str, str], ...]], _Series] = {}
        self._traces: deque[OperationalTrace] = deque(maxlen=max_traces)
        self._dropped_series = 0
        self._lock = Lock()

    def _observe(self, metric: str, labels: dict[str, str], duration_ms: float) -> None:
        metric = _normalize_event(metric)
        duration = _bounded_duration(duration_ms)
        key = (metric, tuple(sorted(labels.items())))
        with self._lock:
            series = self._series.get(key)
            if series is None:
                if len(self._series) >= self._max_series:
                    self._dropped_series += 1
                    return
                series = _Series(self._sample_window)
                self._series[key] = series
            series.observe(duration)

    def _trace(self, operation: str, outcome: str, duration_ms: float, correlation_id: str | None = None) -> None:
        operation = _normalize_event(operation)
        if outcome not in _ALLOWED_OUTCOMES:
            raise ValueError("OBSERVABILITY_OUTCOME_INVALID")
        cid = correlation_id or current_correlation_id() or str(uuid.uuid4())
        if not _REQUEST_ID_PATTERN.fullmatch(cid):
            cid = str(uuid.uuid4())
        trace = OperationalTrace(
            correlation_id=cid,
            operation=operation,
            outcome=outcome,
            duration_ms=_bounded_duration(duration_ms),
            observed_at=datetime.now(UTC),
        )
        with self._lock:
            self._traces.append(trace)

    def record_http(self, *, route: str | None, method: str, status_code: int, duration_ms: float, correlation_id: str) -> None:
        template = normalize_route_template(route)
        verb = method.upper() if method.upper() in _ALLOWED_METHODS else "OTHER"
        status_class = f"{max(0, min(9, int(status_code) // 100))}xx"
        outcome = "success" if 200 <= status_code < 500 else "failure"
        self._observe("http.server.request", {"route": template, "method": verb, "status_class": status_class}, duration_ms)
        # Route is a bounded template supplied by the framework, not a concrete URL.
        operation = f"http.{verb.lower()}.{template.strip('/').replace('/', '.').replace('{', '').replace('}', '') or 'root'}"
        operation = re.sub(r"[^a-z0-9._-]", "_", operation.lower())[:128]
        self._trace(operation, outcome, duration_ms, correlation_id)

    def record_dependency(self, *, component: str, outcome: str, duration_ms: float, correlation_id: str | None = None) -> None:
        if component not in _ALLOWED_DEPENDENCIES:
            raise ValueError("OBSERVABILITY_DEPENDENCY_INVALID")
        if outcome not in _ALLOWED_OUTCOMES:
            raise ValueError("OBSERVABILITY_OUTCOME_INVALID")
        self._observe("dependency.request", {"component": component, "outcome": outcome}, duration_ms)
        self._trace(f"dependency.{component}", outcome, duration_ms, correlation_id)

    def record_companion_event(self, *, event: str, outcome: str = "success", duration_ms: float = 0.0) -> None:
        event_name = _normalize_event(event)
        if not event_name.startswith("companion."):
            raise ValueError("OBSERVABILITY_COMPANION_EVENT_INVALID")
        if outcome not in _ALLOWED_OUTCOMES:
            raise ValueError("OBSERVABILITY_OUTCOME_INVALID")
        self._observe("companion.runtime.event", {"event": event_name, "outcome": outcome}, duration_ms)

    def record_resilience(self, *, scenario: str, outcome: str) -> None:
        scenario_name = _normalize_event(scenario)
        if not scenario_name.startswith("resilience."):
            raise ValueError("OBSERVABILITY_RESILIENCE_EVENT_INVALID")
        if outcome not in {"ready", "degraded", "stopped", "auth_required"}:
            raise ValueError("OBSERVABILITY_RESILIENCE_OUTCOME_INVALID")
        self._observe("resilience.assessment", {"scenario": scenario_name, "outcome": outcome}, 0.0)

    def snapshot(self, *, trace_limit: int = 64) -> dict[str, object]:
        if not 0 <= trace_limit <= 256:
            raise ValueError("OBSERVABILITY_TRACE_SNAPSHOT_LIMIT_INVALID")
        with self._lock:
            series = [
                {
                    "metric": metric,
                    "labels": dict(labels),
                    **state.snapshot(),
                }
                for (metric, labels), state in sorted(self._series.items())
            ]
            traces = list(self._traces)[-trace_limit:] if trace_limit else []
            dropped = self._dropped_series
        return {
            "schema_version": "1.0",
            "series_count": len(series),
            "dropped_series": dropped,
            "series": series,
            "recent_traces": [
                {
                    "correlation_id": trace.correlation_id,
                    "operation": trace.operation,
                    "outcome": trace.outcome,
                    "duration_ms": round(trace.duration_ms, 3),
                    "observed_at": trace.observed_at.isoformat(),
                }
                for trace in traces
            ],
        }

    def reset_for_test(self) -> None:
        with self._lock:
            self._series.clear()
            self._traces.clear()
            self._dropped_series = 0


observability_registry = OperationalObservabilityRegistry()
