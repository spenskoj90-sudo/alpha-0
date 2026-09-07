from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.game_adapter import CapabilityStatus, DataQuality, EvidenceLevel
from app.core.ugs_replay import DeterministicUGSReplay
from app.core.unified_game_state import (
    CombatState,
    UGSIngestor,
    UGSState,
)


BASE = datetime(2026, 9, 7, 8, 0, tzinfo=UTC)


def event(sequence: int) -> dict:
    return {
        "event_id": f"event-{sequence}",
        "schema_version": "1.0",
        "occurred_at": BASE + timedelta(seconds=sequence),
        "sequence": sequence,
        "source": {"adapter_id": "wow-legacy"},
        "event_type": "player.state.changed",
        "payload": {"health": 900},
        "data_quality": "HIGH",
        "provenance": [f"fixture-{sequence}"],
    }


def state(sequence: int, *, observed_at: datetime = BASE, target_health: bool = True) -> UGSState:
    capabilities = {
        "player.state": {"status": "LIMITED", "evidence_level": "L2"},
    }
    if target_health:
        capabilities["target.health"] = {"status": "UNVERIFIED", "evidence_level": "L1"}
    return UGSState(
        schema_version="1.0",
        state_id=f"state-{sequence}",
        session_id="session-1",
        sequence=sequence,
        observed_at=observed_at,
        ingested_at=observed_at + timedelta(milliseconds=5),
        source={"adapter_id": "wow-legacy", "profile": "3.3.5a-test"},
        capabilities=capabilities,
        player={
            "id": "player-1",
            "class": "warrior",
            "combat_state": "IN_COMBAT",
            "alive": True,
        },
        targets=[
            {
                "id": "target-1",
                "type": "npc",
                "hostility": "hostile",
                "health": {"current": 900, "maximum": 1000},
            }
        ],
        events=[event(sequence)],
        data_quality=DataQuality.HIGH,
        provenance=[f"fixture-{sequence}"],
    )


def test_valid_state_preserves_observed_vs_ingested_time() -> None:
    result = state(1)
    assert result.observed_at == BASE
    assert result.ingested_at > result.observed_at
    assert result.player.combat_state == CombatState.IN_COMBAT


def test_unknown_capability_does_not_make_signal_usable() -> None:
    result = state(1)
    ingestor = UGSIngestor()
    assert not ingestor.usable_capability(result, "target.health")


def test_duplicate_and_out_of_order_updates_are_rejected() -> None:
    ingestor = UGSIngestor()
    assert ingestor.accept(state(1))
    assert not ingestor.accept(state(1))
    assert not ingestor.accept(state(0))
    assert ingestor.accept(state(2))
    assert ingestor.last_known_good("session-1").sequence == 2


def test_sessions_have_independent_sequence_spaces() -> None:
    ingestor = UGSIngestor()
    first = state(10)
    second = first.model_copy(update={"session_id": "session-2", "state_id": "state-10-b"})
    assert ingestor.accept(first)
    assert ingestor.accept(second)


def test_stale_state_is_explicitly_degraded() -> None:
    ingestor = UGSIngestor(freshness_seconds=5)
    old = state(1, observed_at=BASE)
    assert ingestor.accept(old)
    expired = ingestor.expire(session_id="session-1", now=BASE + timedelta(seconds=6))
    assert expired.data_quality == DataQuality.UNKNOWN
    assert "stale_state" in expired.missing_signals


def test_fresh_state_is_retained() -> None:
    ingestor = UGSIngestor(freshness_seconds=5)
    current = state(1, observed_at=BASE)
    ingestor.accept(current)
    assert ingestor.expire(session_id="session-1", now=BASE + timedelta(seconds=4)) == current


def test_invalid_timestamp_order_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ingested_at"):
        state(1).model_copy(update={"ingested_at": BASE - timedelta(seconds=1)})


def test_future_event_sequence_is_rejected() -> None:
    payload = state(1).model_dump(mode="python", by_alias=True)
    payload["events"] = [event(2)]
    with pytest.raises(ValidationError, match="event sequence"):
        UGSState.model_validate(payload)


def test_health_cannot_exceed_maximum() -> None:
    payload = state(1).model_dump(mode="python", by_alias=True)
    payload["targets"][0]["health"] = {"current": 1001, "maximum": 1000}
    with pytest.raises(ValidationError, match="current cannot exceed maximum"):
        UGSState.model_validate(payload)


def test_unsupported_extra_fields_are_rejected() -> None:
    payload = state(1).model_dump(mode="python", by_alias=True)
    payload["unexpected"] = "not part of UGS v1"
    with pytest.raises(ValidationError, match="extra"):
        UGSState.model_validate(payload)


def test_replay_is_deterministic_and_round_trips() -> None:
    replay = DeterministicUGSReplay([state(1), state(2)])
    digest = replay.digest()
    assert digest == DeterministicUGSReplay(replay.replay()).digest()
    assert replay.replay() == (state(1), state(2))


def test_replay_rejects_mixed_sessions() -> None:
    first = state(1)
    second = first.model_copy(update={"session_id": "session-2", "state_id": "state-2", "sequence": 2})
    with pytest.raises(ValueError, match="one session"):
        DeterministicUGSReplay([first, second])


def test_replay_rejects_non_monotonic_sequences() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        DeterministicUGSReplay([state(2), state(1)])
