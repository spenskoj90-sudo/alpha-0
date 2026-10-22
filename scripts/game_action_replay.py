#!/usr/bin/env python3
"""Run an explicit observe/recommend/confirm/verify loop in memory only."""
from hashlib import sha256
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.core.action_gateway import ActionGateway
from app.core.knowledge_packs import load_pack
from app.core.offline_game_actions import OfflineActionSession, TurnWorld
from app.core.offline_game_pipeline import OfflineTurnPipeline
from app.core.security import AuthorizationEngine, Decision, Policy, Principal


def main() -> int:
    principal = Principal("offline-fixture", "offline-device", frozenset(), frozenset({"offline:write"}))
    policy = Policy(Decision.ALLOW, "offline:advance", "offline:turn-world",
                    scopes=frozenset({"offline:write"}))
    gateway = ActionGateway(AuthorizationEngine([policy]),
                            entitlement_resolver=lambda _: ("offline-game-test",))
    world = TurnWorld("offline-replay")
    session = OfflineActionSession(world, gateway)
    session.arm(principal, now_ms=1000, expires_ms=11000,
                mode="BOUNDED_RULE", steps=3, confirmed=True)
    fixture = (ROOT / "scripts/fixtures/offline-turn-knowledge.v1.json").read_bytes()
    knowledge = load_pack(fixture, sha256(fixture).hexdigest())
    pipeline = OfflineTurnPipeline(world, session, knowledge)

    outcomes = []
    for step in range(3):
        now = 1000 + step * 1000
        review = pipeline.review(now_ms=now)
        if review.evaluation.status != "ready" or len(review.evaluation.items) != 1:
            return 1
        # Separate, synthetic explicit confirmation for each fixture step.
        # No game UI/user consent or automatic game execution is inferred.
        outcome = pipeline.confirm_fixture_step(
            principal, review, now_ms=now, idempotency_key=f"step-{step}", confirmed=True
        )
        outcomes.append({
            "outcome": outcome.outcome,
            "reason": outcome.reason,
            "sequence": outcome.observed_sequence,
            "observed_before_sequence": review.observation.sequence,
            "recommendation_rule": review.evaluation.items[0]["rule_id"],
            "pack_digest": review.pack_digest,
        })
    session.stop()
    print(json.dumps({
        "schema_version": "sentinel.game-action-replay.v1",
        "evidence": "L2_OFFLINE_FIXTURE",
        "source": "DIRECT_IN_MEMORY_TURN_WORLD_ONLY",
        "target": world.target.model_dump(),
        "outcomes": outcomes,
        "stopped": session.stopped,
        "real_game_execution": "DISABLED",
        "android_calibration": "PENDING",
        "review_after_budget": pipeline.review(now_ms=4000).evaluation.status,
    }, sort_keys=True))
    return 0 if all(item["outcome"] == "SUCCEEDED" for item in outcomes) and world.turn == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
