#!/usr/bin/env python3
"""Run the closed, in-memory action fixture; never opens or controls a game."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

from app.core.action_gateway import ActionGateway
from app.core.offline_game_actions import ActionIntent, OfflineActionSession, TurnWorld
from app.core.security import AuthorizationEngine, Decision, Policy, Principal


def main() -> int:
    principal = Principal("offline-fixture", "offline-device", frozenset(), frozenset({"offline:write"}))
    policy = Policy(Decision.ALLOW, "offline:advance", "offline:turn-world", scopes=frozenset({"offline:write"}))
    gateway = ActionGateway(AuthorizationEngine([policy]), entitlement_resolver=lambda _: ("offline-game-test",))
    world = TurnWorld("offline-replay")
    session = OfflineActionSession(world, gateway)
    session.arm(principal, now_ms=1000, expires_ms=11000, mode="BOUNDED_RULE", steps=3, confirmed=True)
    outcomes = []
    for step in range(3):
        now = 1000 + step * 1000
        state = world.observe(now)
        request = ActionIntent(schema_version="sentinel.game-action.v1", target=world.target, session_id=world.session_id,
            action_id="advance_turn", arguments={}, idempotency_key=f"step-{step}", sequence=state.sequence,
            state_digest=state.digest, expires_ms=now + 3000)
        session.schedule(principal, request, now_ms=now)
        outcome = session.drain(principal, now_ms=now)
        outcomes.append({"outcome": outcome.outcome, "reason": outcome.reason, "sequence": outcome.observed_sequence})
    session.stop()
    print(json.dumps({"schema_version": "sentinel.game-action-replay.v1", "evidence": "L2_OFFLINE_FIXTURE",
        "target": world.target.model_dump(), "outcomes": outcomes, "stopped": session.stopped,
        "real_game_execution": "DISABLED", "android_calibration": "PENDING"}, sort_keys=True))
    return 0 if all(outcome["outcome"] == "SUCCEEDED" for outcome in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
