from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class CompanionLatencySnapshot:
    count: int
    minimum_ms: float | None
    maximum_ms: float | None
    average_ms: float | None
    p95_ms: float | None


class CompanionLatencyStats:
    """Bounded, thread-safe latency statistics for operational evidence."""

    def __init__(self, *, max_samples: int = 1024) -> None:
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        self._max_samples = max_samples
        self._samples: list[float] = []
        self._lock = Lock()

    def observe(self, latency_ms: float) -> None:
        if latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        with self._lock:
            self._samples.append(latency_ms)
            if len(self._samples) > self._max_samples:
                self._samples.pop(0)

    def snapshot(self) -> CompanionLatencySnapshot:
        with self._lock:
            count = len(self._samples)
            if not count:
                return CompanionLatencySnapshot(0, None, None, None, None)
            ordered = sorted(self._samples)
            index = max(0, min(count - 1, int((count - 1) * 0.95)))
            return CompanionLatencySnapshot(
                count=count,
                minimum_ms=ordered[0],
                maximum_ms=ordered[-1],
                average_ms=sum(ordered) / count,
                p95_ms=ordered[index],
            )

    def clear(self) -> None:
        with self._lock:
            self._samples.clear()
