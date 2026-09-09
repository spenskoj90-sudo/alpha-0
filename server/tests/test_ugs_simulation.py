from datetime import datetime, timedelta, timezone

import pytest

from app.core.game_adapter import CapabilityStatus, DataQuality, EvidenceLevel
from app.core.ugs_simulation import (
    DeterministicUGSSimulation,
    UGSSimulationStep,
)
from app.core.unified_game_state import CapabilitySnapshot, SourceIdentity, UGSState


BASE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def state(
    sequence: int,
    *,
    session_id: str = "session-1",
    capability_status: CapabilityStatus = CapabilityStatus.UNVERIFIED,
    evidence_level: EvidenceLevel = EvidenceLevel.L1,
) -> UGSState:
    return UGSState(
        schema_version="1.0",
        state_id=f"state-{sequence}",
        session_id=session_id,
        sequence=sequence,
        observed_at=BASE_TIME + timedelta(seconds=sequence),
        ingested_at=BASE_TIME + timedelta(seconds=sequence, milliseconds=10),
        source=SourceIdentity(adapter_id="test.adapter", profile="simulation"),
        capabilities={
            "player.target": CapabilitySnapshot(
                status=capability_status,
                evidence_level=evidence_level,
            )
        },
        data_quality=DataQuality.HIGH,
    )


def test_simulation_is_deterministic_and_exposes_safe_capability_state() -> None:
    steps = [
        UGSSimulationStep(state(1), BASE_TIME + timedelta(seconds=1)),
        UGSSimulationStep(
            state(2, capability_status=CapabilityStatus.LIMITED),
            BASE_TIME + timedelta(seconds=2),
        ),
    ]

    first = DeterministicUGSSimulation().run(steps)
    second = DeterministicUGSSimulation().run(steps)

    assert first == second
    assert first.digest() == second.digest()
    assert first.observations[0].fresh is True
    assert first.observations[1].usable_capabilities == ("player.target",)


def test_simulation_records_duplicate_rejection_without_mutating_last_good_state() -> None:
    duplicate = state(2)
    result = DeterministicUGSSimulation().run(
        [
            UGSSimulationStep(state(1), BASE_TIME + timedelta(seconds=1)),
            UGSSimulationStep(duplicate, BASE_TIME + timedelta(seconds=2)),
            UGSSimulationStep(duplicate, BASE_TIME + timedelta(seconds=3)),
        ]
    )

    assert [item.accepted for item in result.observations] == [True, True, False]


def test_simulation_marks_stale_state_and_removes_usable_capabilities() -> None:
    result = DeterministicUGSSimulation(freshness_seconds=10).run(
        [
            UGSSimulationStep(
                state(
                    1,
                    capability_status=CapabilityStatus.AVAILABLE,
                    evidence_level=EvidenceLevel.L3,
                ),
                BASE_TIME + timedelta(seconds=30),
            )
        ]
    )

    observation = result.observations[0]
    assert observation.accepted is True
    assert observation.fresh is False
    assert observation.expired is True
    assert observation.usable_capabilities == ()


def test_simulation_rejects_naive_clock() -> None:
    with pytest.raises(ValueError, match="now must include timezone information"):
        DeterministicUGSSimulation().run(
            [UGSSimulationStep(state(1), datetime(2026, 1, 1, 12, 0))]
        )
