"""L2 synthetic-only lifecycle, exact profile/clock/sequence and dependency tests."""
from dataclasses import replace

import pytest

from app.core.game_capability_catalog import catalog
from app.core.game_module_lifecycle_replay import ModuleLifecycleReplay, ReplayFrame
from app.core.game_source_modules import SOURCE_MAP, validate_source_modules


def profile(name: str):
    contract = validate_source_modules(SOURCE_MAP.read_bytes(), catalog())
    return next(p for p in contract.profiles if p.profile_id == name)


WOW = "world-of-warcraft-windows"
ANDROID = "shattered-pixel-dungeon-android"


def frame(fields, *, target=WOW, session="demo", sequence=1,
          observed=1000, kind="session"):
    return ReplayFrame(target, session, sequence, observed, tuple(fields), kind)


def modules(snapshot):
    return {m["id"]: m for m in snapshot["modules"]}


def test_wow_combat_and_economy_replay_observe_checkpoint_and_disjoint_fields():
    replay = ModuleLifecycleReplay(profile(WOW), session_id="demo")
    replay.observe(frame(["normalized_events"], kind="checkpoint"), now_ms=1000)
    first = replay.snapshot(now_ms=1001)
    assert modules(first)["combat"]["lifecycle_status"] == "WAITING_FOR_SOURCE"
    assert modules(first)["economy"]["lifecycle_status"] == "WAITING_FOR_SOURCE"

    replay.observe(frame(["player_health", "target_health", "auction_listings"],
                         sequence=2, observed=1100), now_ms=1100)
    second = replay.snapshot(now_ms=1101)
    assert modules(second)["combat"]["lifecycle_status"] == "L2_SIMULATED_ONLY"
    assert modules(second)["economy"]["lifecycle_status"] == "L2_SIMULATED_ONLY"
    assert second["source_trust"] == "UNVERIFIED"
    assert second["evidence"] == "L2_SYNTHETIC_ONLY"
    assert second["shared_player_state"]["availability"] == "UNKNOWN"
    assert all(m["outputs_available"] == [] and not m["execution_authority"]
               for m in second["modules"])
    assert second["execution_authority"] is False

    # A new checkpoint supersedes every earlier field; it cannot make a
    # SavedVariables state into an ongoing live subscription.
    replay.observe(frame(["normalized_events"], kind="checkpoint",
                         sequence=3, observed=1200), now_ms=1200)
    third = replay.snapshot(now_ms=1200)
    assert modules(third)["combat"]["missing_signals"] == ["player_health", "target_health"]
    assert modules(third)["economy"]["missing_signals"] == ["auction_listings"]


def test_android_combat_and_character_simulation_never_attests_capture():
    replay = ModuleLifecycleReplay(profile(ANDROID), session_id="local-capture")
    replay.observe(frame(["health_candidate", "player_health"], target=ANDROID,
                         session="local-capture", kind="session"), now_ms=1000)
    first = replay.snapshot(now_ms=1000)
    assert modules(first)["combat"]["lifecycle_status"] == "L2_SIMULATED_ONLY"
    assert modules(first)["character_build"]["lifecycle_status"] == "WAITING_FOR_SOURCE"
    replay.observe(frame(["inventory"], target=ANDROID, session="local-capture",
                         sequence=2, observed=1100), now_ms=1100)
    second = replay.snapshot(now_ms=1100)
    assert modules(second)["character_build"]["lifecycle_status"] == "L2_SIMULATED_ONLY"
    assert second["shared_player_state"]["session_binding"] is None
    assert second["shared_player_state"]["last_updated_ms"] is None
    assert modules(second)["combat"]["outputs_available"] == []


def test_module_dependency_blocks_l2_presentation_until_all_inputs_arrive():
    android = profile(ANDROID)
    combat, character = android.modules
    character = character.model_copy(update={"dependencies": ("combat",)})
    android = android.model_copy(update={"modules": (combat, character)})
    replay = ModuleLifecycleReplay(android, session_id="a")
    replay.observe(frame(["inventory"], target=ANDROID, session="a"), now_ms=1000)
    first = modules(replay.snapshot(now_ms=1000))
    assert first["character_build"]["lifecycle_status"] == "BLOCKED_BY_DEPENDENCY"
    replay.observe(frame(["health_candidate", "player_health"], target=ANDROID,
                         session="a", sequence=2, observed=1010), now_ms=1010)
    assert modules(replay.snapshot(now_ms=1010))["character_build"]["lifecycle_status"] == "L2_SIMULATED_ONLY"


def test_stale_source_is_unknown_even_when_previously_simulated_and_stop_latches():
    replay = ModuleLifecycleReplay(profile(ANDROID), session_id="a")
    replay.observe(frame(["health_candidate", "player_health"], target=ANDROID,
                         session="a"), now_ms=1000)
    assert modules(replay.snapshot(now_ms=6000))["combat"]["lifecycle_status"] == "L2_SIMULATED_ONLY"
    stale = replay.snapshot(now_ms=6001)
    assert modules(stale)["combat"]["lifecycle_status"] == "WAITING_FOR_SOURCE"
    assert stale["shared_player_state"]["availability"] == "UNKNOWN"
    replay.stop()
    stopped = replay.snapshot(now_ms=6002)
    assert stopped["session_id"] is None
    assert all(m["lifecycle_status"] == "STOPPED" for m in stopped["modules"])
    with pytest.raises(ValueError, match="REPLAY_STOPPED"):
        replay.observe(frame(["inventory"], target=ANDROID, session="a",
                             sequence=2, observed=6002), now_ms=6002)


@pytest.mark.parametrize("bad,now,error", [
    (frame(["player_health"], session="other"), 1000, "REPLAY_PROFILE_SESSION_MISMATCH"),
    (frame(["player_health"], target=ANDROID), 1000, "REPLAY_PROFILE_SESSION_MISMATCH"),
    (frame(["nonexistent"]), 1000, "REPLAY_FIELD_NOT_DECLARED"),
    (frame(["player_health", "player_health"]), 1000, "REPLAY_FIELDS_DUPLICATE"),
    (frame([]), 1000, "REPLAY_FIELDS_INVALID"),
    (frame(["normalized_events"]), 1000, "REPLAY_CHECKPOINT_REQUIRED"),
    (frame(["health_candidate"], target=WOW, kind="checkpoint"), 1000, "REPLAY_FIELD_NOT_DECLARED"),
    (frame(["player_health"], sequence=2), 1000, "REPLAY_SEQUENCE_INVALID"),
    (frame(["player_health"], sequence=True), 1000, "REPLAY_SEQUENCE_INVALID"),
    (frame(["player_health"], observed=1001), 1000, "REPLAY_STALE_SOURCE"),
    (frame(["player_health"], observed=100), 5101, "REPLAY_STALE_SOURCE"),
])
def test_invalid_first_frame_is_atomic(bad, now, error):
    replay = ModuleLifecycleReplay(profile(WOW), session_id="demo")
    with pytest.raises(ValueError, match=error):
        replay.observe(bad, now_ms=now)
    assert replay.snapshot(now_ms=1000)["sequence"] == 0
    assert not modules(replay.snapshot(now_ms=1000))["combat"]["synthetic_signals"]


def test_replay_rejects_duplicate_sequence_clock_rollback_and_lost_checkpoint_kind():
    replay = ModuleLifecycleReplay(profile(WOW), session_id="demo")
    replay.observe(frame(["normalized_events"], kind="checkpoint"), now_ms=1000)
    for item, now, reason in (
        (frame(["auction_listings"], kind="session"), 1001, "REPLAY_SEQUENCE_INVALID"),
        (frame(["auction_listings"], sequence=2, observed=999), 1001, "REPLAY_CLOCK_ROLLBACK"),
        (frame(["auction_listings"], sequence=2, observed=1002), 1001, "REPLAY_STALE_SOURCE"),
        (frame(["normalized_events"], kind="session", sequence=2, observed=1001),
         1001, "REPLAY_CHECKPOINT_REQUIRED"),
    ):
        with pytest.raises(ValueError, match=reason):
            replay.observe(item, now_ms=now)
        assert replay.snapshot(now_ms=1001)["sequence"] == 1
    replay.observe(frame(["auction_listings"], sequence=2, observed=1002), now_ms=1002)
    assert replay.snapshot(now_ms=1002)["sequence"] == 2
    with pytest.raises(ValueError, match="REPLAY_CLOCK_ROLLBACK"):
        replay.snapshot(now_ms=1001)
    with pytest.raises(ValueError, match="REPLAY_CLOCK_INVALID"):
        replay.snapshot(now_ms=True)


def test_replay_never_exposes_game_data_or_accepts_arbitrary_runtime_capabilities():
    replay = ModuleLifecycleReplay(profile(WOW), session_id="demo")
    original = replay.snapshot(now_ms=0)
    for module in original["modules"]:
        assert set(module) == {
            "id", "lifecycle_status", "missing_signals", "synthetic_signals",
            "outputs_available", "execution_authority",
        }
    for invalid in ("", "x" * 129, None, False):
        with pytest.raises(ValueError, match="REPLAY_IDENTITY_INVALID"):
            ModuleLifecycleReplay(profile(WOW), session_id=invalid)
    with pytest.raises(ValueError, match="REPLAY_IDENTITY_INVALID"):
        ModuleLifecycleReplay(object(), session_id="demo")

def test_android_ocr_cannot_be_relabelled_as_a_checkpoint():
    replay = ModuleLifecycleReplay(profile(ANDROID), session_id="demo")
    with pytest.raises(ValueError, match="REPLAY_SESSION_REQUIRED"):
        replay.observe(frame(["health_candidate"], target=ANDROID,
                             kind="checkpoint"), now_ms=1000)
    assert replay.snapshot(now_ms=1000)["sequence"] == 0
    assert not modules(replay.snapshot(now_ms=1000))["combat"]["synthetic_signals"]
    replay.observe(frame(["health_candidate"], target=ANDROID,
                         kind="session"), now_ms=1000)
    assert replay.snapshot(now_ms=1000)["sequence"] == 1


def test_checkpoint_rejection_preserves_prior_session_observation():
    replay = ModuleLifecycleReplay(profile(ANDROID), session_id="demo")
    replay.observe(frame(["health_candidate"], target=ANDROID), now_ms=1000)
    before = replay.snapshot(now_ms=1001)
    with pytest.raises(ValueError, match="REPLAY_SESSION_REQUIRED"):
        replay.observe(frame(["health_candidate"], target=ANDROID,
                             sequence=2, observed=1002, kind="checkpoint"), now_ms=1002)
    after = replay.snapshot(now_ms=1002)
    assert after["sequence"] == before["sequence"] == 1
    assert modules(after)["combat"]["synthetic_signals"] == ["health_candidate"]
