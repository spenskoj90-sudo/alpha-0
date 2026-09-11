from datetime import datetime, timezone

from app.core.companion_latency_stats import CompanionLatencyStats
from app.core.companion_protocol import CompanionMode
from app.core.companion_transport import CompanionRuntimeHealth
from app.core.companion_health_metrics import companion_health_metrics


def test_health_metrics_preserve_health_and_latency_evidence():
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    stats = CompanionLatencyStats()
    stats.observe(10.0)
    stats.observe(20.0)
    health = CompanionRuntimeHealth(CompanionMode.ACTIVE, now, 20.0, 1, 2, 3, now, False, True, "peer-a")
    result = companion_health_metrics(health, stats.snapshot())
    assert result["mode"] == "ACTIVE"
    assert result["queue_depth"] == 2
    assert result["latency"]["count"] == 2
    assert result["latency"]["p95_ms"] == 20.0
