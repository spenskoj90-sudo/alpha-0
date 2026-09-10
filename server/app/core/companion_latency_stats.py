from __future__ import annotations

from bisect import insort
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
            insort(self._samples, latency_ms)
            if len(self._samples) > self._max_samples:
                self._samples.pop(0)

    def snapshot(self) -> CompanionLatencySnapshot:
        with self._lock:
            count = len(self._samples)
            if not count:
                return CompanionLatencySnapshot(0, None, None, None, None)
            index = max(0, min(count - 1, int((count - 1) * 0.95)))
            return CompanionLatencySnapshot(
                count=count,
                minimum_ms=self._samples[0],
                maximum_ms=self._samples[-1],
                average_ms=sum(self._samples) / count,
                p95_ms=self._samples[index],
            )

    def clear(self) -> None:
        with self._lock:
            self._samples.clear()
