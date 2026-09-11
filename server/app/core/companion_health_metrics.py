from __future__ import annotations

from typing import Any

from .companion_health_api import companion_health_response
from .companion_latency_stats import CompanionLatencySnapshot
from .companion_transport import CompanionRuntimeHealth


def companion_health_metrics(
    health: CompanionRuntimeHealth,
    latency: CompanionLatencySnapshot,
) -> dict[str, Any]:
    """Compose bounded runtime health and measured latency evidence."""
    response = companion_health_response(health)
    response["latency"] = {
        "count": latency.count,
        "minimum_ms": latency.minimum_ms,
        "maximum_ms": latency.maximum_ms,
        "average_ms": latency.average_ms,
        "p95_ms": latency.p95_ms,
    }
    return response
