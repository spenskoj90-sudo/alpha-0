"""Closed-world observe -> recommend -> confirmed action -> outcome fixture.

No HTTP route, platform input, external game source, pack publishing, or execution
entitlement exists here. This bridge only accepts the exact in-memory TurnWorld.
"""
from __future__ import annotations

from dataclasses import dataclass

from .knowledge_packs import Evaluation, LoadedPack, evaluate
from .offline_game_actions import (
    ActionIntent, FIXTURE_TARGET, Observation, OfflineActionSession, Outcome, TurnWorld,
)
from .security import Principal

REVIEW_MAX_AGE_MS = 1000
FIXTURE_RULE_ID = "advance-turn"


@dataclass(frozen=True, slots=True)
class TurnReview:
    """A source-bound fixture snapshot and explanation, not execution authority."""
    observation: Observation
    evaluation: Evaluation
    pack_digest: str
    session_id: str


class OfflineTurnPipeline:
    """Single-threaded fixture wiring; real game adapters cannot enter this type boundary."""

    def __init__(self, world: TurnWorld, session: OfflineActionSession, knowledge: LoadedPack):
        if type(world) is not TurnWorld or type(session) is not OfflineActionSession or \
                session.world is not world or world.target != FIXTURE_TARGET:
            raise ValueError("OFFLINE_FIXTURE_ONLY")
        self.world = world
        self.session = session
        self.knowledge = knowledge
        self.session_id = world.session_id

    def review(self, *, now_ms: int, locale: str = "en") -> TurnReview:
        if type(now_ms) is not int or now_ms <= 0:
            raise ValueError("CLOCK_INVALID")
        if self.world.session_id != self.session_id or self.world.target != FIXTURE_TARGET:
            raise ValueError("SESSION_CHANGED")
        snapshot = self.world.observe(now_ms)
        # "source_verified" means only an exact, directly observed local fixture;
        # never infer this value from an incoming client/game payload.
        observation = {
            "game": FIXTURE_TARGET.game,
            "platform": "windows",
            "patch": FIXTURE_TARGET.version,
            "environment": FIXTURE_TARGET.environment,
            "profile": FIXTURE_TARGET.profile,
            "session_id": self.session_id,
            "source_verified": True,
            "observed_at_ms": snapshot.observed_ms,
            "signals": {"turn": snapshot.turn},
        }
        result = evaluate(self.knowledge, observation, now_ms=now_ms,
                          session_id=self.session_id, locale=locale)
        return TurnReview(snapshot, result, self.knowledge.digest, self.session_id)

    @staticmethod
    def _recommended(review: TurnReview) -> bool:
        return review.evaluation.status == "ready" and any(
            item.get("kind") == "recommendation" and item.get("rule_id") == FIXTURE_RULE_ID
            for item in review.evaluation.items
        )

    def confirm_fixture_step(self, principal: Principal, reviewed: TurnReview, *,
                             now_ms: int, idempotency_key: str, confirmed: bool) -> Outcome:
        # A suggestion and/or an existing bounded lease is never a consent click.
        if confirmed is not True:
            raise ValueError("CONFIRMATION_REQUIRED")
        if type(reviewed) is not TurnReview or reviewed.session_id != self.session_id:
            raise ValueError("REVIEW_INVALID")
        if type(now_ms) is not int or not 0 <= now_ms - reviewed.observation.observed_ms <= REVIEW_MAX_AGE_MS:
            raise ValueError("REVIEW_STALE")
        # A changed world/session is operational drift, not a forged review.
        # Preserve these exact reasons before independently checking integrity.
        current = self.review(now_ms=now_ms)
        if current.observation.digest != reviewed.observation.digest or \
                current.observation.sequence != reviewed.observation.sequence:
            raise ValueError("STATE_CHANGED")
        # A review is a caller-held object, not a signed capability. Recompute
        # the original source snapshot before considering the proposed rule.
        if reviewed.observation != self.world.observe(reviewed.observation.observed_ms):
            raise ValueError("REVIEW_TAMPERED")
        if reviewed.pack_digest != self.knowledge.digest or not self._recommended(reviewed):
            raise ValueError("RECOMMENDATION_UNAVAILABLE")
        # Recommendation items contain observed_at_ms. Compare their contents
        # at the original timestamp so valid short-delay consent still works.
        original = self.review(now_ms=reviewed.observation.observed_ms)
        if reviewed.evaluation != original.evaluation:
            raise ValueError("RECOMMENDATION_UNAVAILABLE")
        # A pack's prose/rule is not an action grant. The *independent* compiled
        # fixture step guard is rechecked before the ActionGateway checks.
        if not self._recommended(current) or current.observation.turn >= 3:
            raise ValueError("RECOMMENDATION_UNAVAILABLE")
        request = ActionIntent(
            schema_version="sentinel.game-action.v1",
            target=FIXTURE_TARGET,
            session_id=self.session_id,
            action_id="advance_turn",
            arguments={},
            idempotency_key=idempotency_key,
            sequence=current.observation.sequence,
            state_digest=current.observation.digest,
            expires_ms=now_ms + 3000,
        )
        previous = self.session.schedule(principal, request, now_ms=now_ms)
        if previous is not None:
            return previous
        result = self.session.drain(principal, now_ms=now_ms)
        if result is None:
            raise RuntimeError("FIXTURE_OUTCOME_MISSING")
        return result
