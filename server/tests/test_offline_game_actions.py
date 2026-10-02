from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.core.action_gateway import ActionGateway
from app.core.offline_game_actions import ActionIntent, OfflineActionSession, TurnWorld
from app.core.security import AuthorizationEngine, Decision, Policy, Principal


def setup_session(*, mode="USER_CONFIRMED", fault=None, entitlements=None):
    principal = Principal("fixture-user", "fixture-device", frozenset(), frozenset({"offline:write"}))
    policy = AuthorizationEngine([Policy(Decision.ALLOW, "offline:advance", "offline:turn-world", scopes=frozenset({"offline:write"}))])
    gateway = ActionGateway(policy, entitlement_resolver=entitlements or (lambda _: ("offline-game-test",)))
    world = TurnWorld("fixture-session", fault=fault)
    session = OfflineActionSession(world, gateway)
    session.arm(principal, now_ms=1000, expires_ms=11000, mode=mode, steps=3 if mode == "BOUNDED_RULE" else 1, confirmed=True)
    return session, world, principal


def intent(world, key="request-1", *, now_ms=1000, **changes):
    state = world.observe(now_ms)
    data = dict(schema_version="sentinel.game-action.v1", target=world.target, session_id=world.session_id,
                action_id="advance_turn", arguments={}, idempotency_key=key, sequence=state.sequence,
                state_digest=state.digest, expires_ms=now_ms + 3000)
    data.update(changes)
    return ActionIntent(**data)


def test_confirmed_action_requires_new_matching_observed_outcome_and_duplicate_never_reexecutes():
    session, world, principal = setup_session()
    request = intent(world)
    session.schedule(principal, request, now_ms=1000)
    result = session.drain(principal, now_ms=1001)
    assert result.outcome == "SUCCEEDED"
    assert result.observed_sequence == 1 and world.turn == 1
    assert session.schedule(principal, request, now_ms=1002) == result
    assert world.turn == 1


@pytest.mark.parametrize("fault", ["missing_outcome", "wrong_outcome", "exception"])
def test_uncertain_side_effect_stops_and_is_never_blindly_retried(fault):
    session, world, principal = setup_session(fault=fault)
    request = intent(world)
    session.schedule(principal, request, now_ms=1000)
    result = session.drain(principal, now_ms=1001)
    assert result.outcome == "UNKNOWN"
    assert session.stopped
    assert session.schedule(principal, request, now_ms=1002) == result
    assert world.turn == (2 if fault == "wrong_outcome" else 1)
    with pytest.raises(ValueError, match="STOPPED"):
        session.schedule(principal, intent(world, "new-request", now_ms=1002), now_ms=1002)


@pytest.mark.parametrize("boundary", ["override", "lock", "capture_revoke", "dialog", "loading", "death", "low_confidence", "window_change", "version_change"])
def test_context_invalidation_clears_scheduling_and_leaves_game_independent(boundary):
    session, world, principal = setup_session()
    session.schedule(principal, intent(world), now_ms=1000)
    session.stop(boundary)
    assert session.pending is None and session.stopped
    assert session.drain(principal, now_ms=1001) is None
    assert world.turn == 0
    world.advance()  # the ordinary fixture remains usable with SENTINEL stopped
    assert world.turn == 1


@pytest.mark.parametrize("change", ["principal", "target", "sequence", "digest", "stale", "deadline", "entitlement"])
def test_revalidates_all_boundaries_at_dispatch(change):
    grants = ["offline-game-test"]
    session, world, principal = setup_session(entitlements=lambda _: tuple(grants))
    request = intent(world)
    session.schedule(principal, request, now_ms=1000)
    now = 1001
    if change == "principal":
        principal = replace(principal, device_id="other-device")
    elif change == "target":
        world.session_id = "another-session"
    elif change == "sequence":
        world.advance()
    elif change == "digest":
        world.turn = 9
    elif change == "stale":
        now = 2501
    elif change == "deadline":
        now = 11000
    elif change == "entitlement":
        grants.clear()
    result = session.drain(principal, now_ms=now)
    assert result.outcome == "CANCELLED"
    assert session.stopped and session.pending is None
    assert world.turn == (1 if change == "sequence" else 9 if change == "digest" else 0)


def test_bounded_rule_has_static_condition_rate_and_step_limit():
    session, world, principal = setup_session(mode="BOUNDED_RULE")
    for step in range(3):
        now = 1000 + step * 1000
        session.schedule(principal, intent(world, f"step-{step}", now_ms=now), now_ms=now)
        assert session.drain(principal, now_ms=now).outcome == "SUCCEEDED"
    with pytest.raises(ValueError, match="BUDGET"):
        session.schedule(principal, intent(world, "excess", now_ms=4000), now_ms=4000)
    assert world.turn == 3


def test_rate_queue_idempotency_conflict_and_backwards_clock_fail_closed():
    session, world, principal = setup_session(mode="BOUNDED_RULE")
    first = intent(world)
    session.schedule(principal, first, now_ms=1000)
    with pytest.raises(ValueError, match="QUEUE_FULL"):
        session.schedule(principal, intent(world, "another"), now_ms=1000)
    assert session.drain(principal, now_ms=1000).outcome == "SUCCEEDED"
    with pytest.raises(ValueError, match="IDEMPOTENCY_CONFLICT"):
        session.schedule(principal, intent(world), now_ms=1001)
    with pytest.raises(ValueError, match="RATE_LIMIT"):
        session.schedule(principal, intent(world, "rate", now_ms=1001), now_ms=1001)
    with pytest.raises(ValueError, match="CLOCK_ROLLBACK"):
        session.schedule(principal, intent(world, "clock", now_ms=999), now_ms=999)


@pytest.mark.parametrize("changes", [{"schema_version": "2"}, {"action_id": "shell"}, {"arguments": {"url": "https://example.invalid"}}, {"sequence": True}, {"state_digest": "bad"}, {"script": "arbitrary"}])
def test_request_schema_rejects_executable_payloads_and_coercion(changes):
    _, world, _ = setup_session()
    with pytest.raises(ValidationError):
        intent(world, **changes)


def test_no_arm_without_explicit_confirmation_or_authenticated_device():
    session, _, principal = setup_session()
    for changes in ({"confirmed": False}, {"expires_ms": 32000}, {"steps": 4}, {"mode": "AUTOMATIC"}):
        unarmed = OfflineActionSession(TurnWorld("fixture-session"), session.gateway)
        args = dict(now_ms=1000, expires_ms=11000, mode="USER_CONFIRMED", steps=1, confirmed=True)
        args.update(changes)
        with pytest.raises(ValueError):
            unarmed.arm(principal, **args)
    unarmed = OfflineActionSession(TurnWorld("fixture-session"), session.gateway)
    with pytest.raises(ValueError, match="PRINCIPAL"):
        unarmed.arm(replace(principal, device_id=None), now_ms=1000, expires_ms=11000, mode="USER_CONFIRMED", steps=1, confirmed=True)


def test_wrong_target_and_long_expiry_cannot_enter_queue():
    session, world, principal = setup_session()
    for changes in ({"target": world.target.model_copy(update={"package": "com.shatteredpixel.shatteredpixeldungeon"})}, {"expires_ms": 5001}):
        with pytest.raises(ValueError):
            session.schedule(principal, intent(world, **changes), now_ms=1000)
    assert session.pending is None and world.turn == 0
