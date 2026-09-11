from __future__ import annotations

from datetime import datetime

from .companion_latency_stats import CompanionLatencySnapshot
from .companion_runtime import CompanionRuntime


def measure_latency_samples(
    runtime: CompanionRuntime,
    samples: list[tuple[datetime, datetime]],
) -> CompanionLatencySnapshot:
    """Record supplied end-to-end timestamps and return reproducible statistics.

    The function performs no sleeping, wall-clock sampling, network I/O, or
    claims about a production environment. Callers must provide measured pairs.
    """
    for sent_at, received_at in samples:
        runtime.observe_latency(sent_at, received_at)
    return runtime.latency_stats.snapshot()
