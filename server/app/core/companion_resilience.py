from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .companion_protocol import CompanionMode
from .companion_transport import CompanionRuntimeHealth


class ResilienceOutcome(StrEnum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    STOPPED = "STOPPED"
    AUTH_REQUIRED = "AUTH_REQUIRED"


@dataclass(frozen=True, slots=True)
class ResilienceCase:
    name: str
    trigger: str
    expected_outcome: ResilienceOutcome
    recovery: str


RECOVERY_MATRIX: tuple[ResilienceCase, ...] = (
    ResilienceCase("heartbeat-timeout", "missing heartbeat", ResilienceOutcome.DEGRADED, "heartbeat then reconnect"),
    ResilienceCase("transport-failure", "send failure", ResilienceOutcome.DEGRADED, "bounded exponential reconnect"),
    ResilienceCase("peer-auth-failure", "invalid peer evidence", ResilienceOutcome.AUTH_REQUIRED, "reauthenticate explicitly"),
    ResilienceCase("kill-switch", "local latch active", ResilienceOutcome.STOPPED, "explicit reset then fresh connect"),
    ResilienceCase("queue-backpressure", "bounded queue full", ResilienceOutcome.DEGRADED, "drop oldest with telemetry"),
)


def validate_recovery_matrix(cases: tuple[ResilienceCase, ...] = RECOVERY_MATRIX) -> tuple[ResilienceCase, ...]:
    """Validate the documented failure/recovery cases deterministically."""
    if not cases or len(cases) > 32:
        raise ValueError("recovery matrix must contain between 1 and 32 cases")
    names = [case.name for case in cases]
    if any(not name or len(name) > 128 for name in names) or len(set(names)) != len(names):
        raise ValueError("recovery case names must be unique and bounded")
    return cases


def assess_health(health: CompanionRuntimeHealth) -> ResilienceOutcome:
    if health.kill_switch_active or health.mode is CompanionMode.STOPPED:
        return ResilienceOutcome.STOPPED
    if not health.peer_authenticated:
        return ResilienceOutcome.AUTH_REQUIRED
    if health.mode is CompanionMode.DEGRADED or health.dropped_events > 0:
        return ResilienceOutcome.DEGRADED
    return ResilienceOutcome.READY

