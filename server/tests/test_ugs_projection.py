from datetime import UTC, datetime

import pytest

from app.core.game_adapter import DataQuality
from app.core.ugs_projection import UGSProjectionRegistry
from app.core.unified_game_state import SourceIdentity, UGSState


def state(sequence: int, session_id: str = "session-1") -> UGSState:
    observed = datetime(2026, 1, 1, 12, 0, sequence, tzinfo=UTC)
    return UGSState(
        schema_version="1.0",
        state_id=f"state-{sequence}",
        session_id=session_id,
        sequence=sequence,
        observed_at=observed,
        ingested_at=observed,
        source=SourceIdentity(adapter_id="test.adapter", profile="test"),
        data_quality=DataQuality.HIGH,
    )


def test_registry_applies_all_projections_in_stable_order() -> None:
    seen: list[str] = []
    registry = UGSProjectionRegistry()
    registry.register("z-last", lambda item: seen.append(f"z:{item.sequence}"))
    registry.register("a-first", lambda item: seen.append(f"a:{item.sequence}"))

    result = registry.apply(state(1))

    assert result.applied == ("a-first", "z-last")
    assert seen == ["a:1", "z:1"]
    assert registry.names() == ("a-first", "z-last")


def test_registry_rejects_duplicate_sequence_without_reapplying() -> None:
    calls: list[int] = []
    registry = UGSProjectionRegistry()
    registry.register("characters", lambda item: calls.append(item.sequence))
    registry.apply(state(1))

    with pytest.raises(ValueError, match="PROJECTION_SEQUENCE_REPLAY"):
        registry.apply(state(1))

    assert calls == [1]


def test_replay_requires_strict_session_order() -> None:
    registry = UGSProjectionRegistry()
    registry.register("characters", lambda _: None)

    with pytest.raises(ValueError, match="PROJECTION_REPLAY_ORDER"):
        registry.replay([state(2), state(1)])

    with pytest.raises(ValueError, match="PROJECTION_REPLAY_ORDER"):
        registry.replay([state(1), state(2, "other-session")])


def test_replay_is_deterministic_for_same_input() -> None:
    states = [state(1), state(2)]
    first: list[tuple[str, int]] = []
    second: list[tuple[str, int]] = []

    first_registry = UGSProjectionRegistry()
    first_registry.register("projection", lambda item: first.append((item.state_id, item.sequence)))
    second_registry = UGSProjectionRegistry()
    second_registry.register("projection", lambda item: second.append((item.state_id, item.sequence)))

    assert first_registry.replay(states) == second_registry.replay(states)
    assert first == second == [("state-1", 1), ("state-2", 2)]
