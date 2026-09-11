from datetime import datetime, timezone

from app.core.companion_health_api import companion_health_response
from app.core.companion_protocol import CompanionMode
from app.core.companion_transport import CompanionRuntimeHealth


def test_health_response_is_bounded_and_json_ready():
    heartbeat = datetime(2026, 9, 11, tzinfo=timezone.utc)
    health = CompanionRuntimeHealth(
        mode=CompanionMode.DEGRADED,
        last_heartbeat=heartbeat,
        last_latency_ms=37.0,
        reconnect_attempts=2,
        queue_depth=1,
        dropped_events=3,
        last_successful_send=None,
        kill_switch_active=False,
        peer_authenticated=True,
        peer_id="peer-a",
    )

    assert companion_health_response(health) == {
        "mode": "DEGRADED",
        "last_heartbeat": "2026-09-11T00:00:00+00:00",
        "last_latency_ms": 37.0,
        "reconnect_attempts": 2,
        "queue_depth": 1,
        "dropped_events": 3,
        "last_successful_send": None,
        "kill_switch_active": False,
        "peer_authenticated": True,
        "peer_id": "peer-a",
    }
