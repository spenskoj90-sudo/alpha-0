from datetime import UTC, datetime

import pytest

from app.core.companion_protocol import CompanionMode
from app.core.companion_resilience import (
    RECOVERY_MATRIX,
    ResilienceOutcome,
    assess_health,
    validate_recovery_matrix,
)
from app.core.companion_transport import CompanionRuntimeHealth


def health(*, mode=CompanionMode.ACTIVE, authenticated=True, dropped=0, kill=False):
    return CompanionRuntimeHealth(
        mode=mode,
        last_heartbeat=datetime(2026, 9, 12, tzinfo=UTC),
        last_latency_ms=20.0,
        reconnect_attempts=0,
        queue_depth=0,
        dropped_events=dropped,
        last_successful_send=None,
        kill_switch_active=kill,
        peer_authenticated=authenticated,
        peer_id="peer-1" if authenticated else None,
    )


def test_recovery_matrix_is_unique_and_health_assessment_is_fail_closed():
    assert len(validate_recovery_matrix()) == len(RECOVERY_MATRIX)
    assert assess_health(health()) is ResilienceOutcome.READY
    assert assess_health(health(mode=CompanionMode.DEGRADED)) is ResilienceOutcome.DEGRADED
    assert assess_health(health(authenticated=False)) is ResilienceOutcome.AUTH_REQUIRED
    assert assess_health(health(kill=True)) is ResilienceOutcome.STOPPED
    assert assess_health(health(dropped=1)) is ResilienceOutcome.DEGRADED


def test_recovery_matrix_rejects_duplicate_case_names():
    with pytest.raises(ValueError, match="unique"):
        validate_recovery_matrix((RECOVERY_MATRIX[0], RECOVERY_MATRIX[0]))

