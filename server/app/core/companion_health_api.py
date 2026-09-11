from __future__ import annotations

from typing import Any

from .companion_transport import CompanionRuntimeHealth


def companion_health_response(health: CompanionRuntimeHealth) -> dict[str, Any]:
    """Serialize the bounded runtime health snapshot without transport internals."""

    return {
        "mode": health.mode.value,
        "last_heartbeat": health.last_heartbeat.isoformat() if health.last_heartbeat else None,
        "last_latency_ms": health.last_latency_ms,
        "reconnect_attempts": health.reconnect_attempts,
        "queue_depth": health.queue_depth,
        "dropped_events": health.dropped_events,
        "last_successful_send": health.last_successful_send.isoformat()
        if health.last_successful_send
        else None,
        "kill_switch_active": health.kill_switch_active,
        "peer_authenticated": health.peer_authenticated,
        "peer_id": health.peer_id,
    }
