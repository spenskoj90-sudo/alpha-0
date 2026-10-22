"""Exact offline fixture pipeline: every step remains source-bound and policy-gated."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from app.core.action_gateway import ActionGateway
from app.core.knowledge_packs import PackRegistry, load_pack
from app.core.offline_game_actions import OfflineActionSession, TurnWorld
from app.core.offline_game_pipeline import OfflineTurnPipeline
from app.core.security import AuthorizationEngine, Decision, Policy, Principal

FIXTURE = Path(__file__).resolve().parents[2] / "scripts/fixtures/offline-turn-knowledge.v1.json"


def setup_pipeline(*, fault=None, change_pack=None, registry=None, entitlements=None):
    principal = Principal("fixture-user", "fixture-device", frozenset(), frozenset({"offline:write"}))
    policy = Policy(Decision.ALLOW, "offline:advance", "offline:turn-world",
                    scopes=frozenset({"offline:write"}))
    gateway = ActionGateway(AuthorizationEngine([policy]), entitlement_resolver=(
        entitlements if entitlements is not None else lambda _: ("offline-game-test",)
    ))
    world = TurnWorld("fixture-pipeline", fault=fault)
    session = OfflineActionSession(world, gateway)
    session.arm(principal, now_ms=1000, expires_ms=11000, mode="BOUNDED_RULE",
                steps=3, confirmed=True)
    raw = FIXTURE.read_bytes() if change_pack is None else change_pack
    digest = sha256(raw).hexdigest()
    if registry is not None:
        registry = PackRegistry(registry, allowed_digests={digest})
        registry.put(raw, digest)
        loaded = registry.get(digest)
    else:
        loaded = load_pack(raw, digest)
    return OfflineTurnPipeline(world, session, loaded), world, session, principal, registry


def test_review_has_provenance_but_never_action_authority():
    pipeline, world, session, _, _ = setup_pipeline()
    reviewed = pipeline.review(now_ms=1000, locale="ru")
    assert reviewed.evaluation.status == "ready"
    item, = reviewed.evaluation.items
    assert item["rule_id"] == "advance-turn"
    assert item["kind"] == "recommendation" and item["confidence"] is None
    assert item["text"].startswith("Рассмотрите")
    assert "execute" not in item and "action" not in item
    assert reviewed.observation.digest == world.observe(1000).digest
    assert session.pending is None and world.turn == 0


def test_three_explicitly_confirmed_turns_have_observed_outcomes():
    pipeline, world, session, principal, _ = setup_pipeline()
    for step in range(3):
        now = 1000 + 1000 * step
        reviewed = pipeline.review(now_ms=now)
        result = pipeline.confirm_fixture_step(principal, reviewed, now_ms=now,
                                               idempotency_key=f"step-{step}", confirmed=True)
        assert result.outcome == "SUCCEEDED"
        assert result.observed_sequence == step + 1
        assert world.turn == step + 1
    assert pipeline.review(now_ms=4000).evaluation.status == "empty"
    assert session.pending is None


def test_no_consent_means_no_queue_or_action():
    pipeline, world, session, principal, _ = setup_pipeline()
    reviewed = pipeline.review(now_ms=1000)
    for consent in (False, None, 1, "true"):
        with pytest.raises(ValueError, match="CONFIRMATION_REQUIRED"):
            pipeline.confirm_fixture_step(principal, reviewed, now_ms=1000,
                                          idempotency_key="blocked", confirmed=consent)
    assert world.turn == 0 and session.pending is None


@pytest.mark.parametrize("scenario,reason", [
    ("stale", "REVIEW_STALE"), ("clock", "REVIEW_STALE"),
    ("world_advanced", "STATE_CHANGED"), ("session_changed", "SESSION_CHANGED"),
])
def test_review_is_bound_to_exact_fresh_state(scenario, reason):
    pipeline, world, session, principal, _ = setup_pipeline()
    reviewed = pipeline.review(now_ms=1000)
    now = 1000
    if scenario == "stale":
        now = 2001
    elif scenario == "clock":
        now = 999
    elif scenario == "world_advanced":
        world.advance()
    elif scenario == "session_changed":
        world.session_id = "replacement-session"
    with pytest.raises(ValueError, match=reason):
        pipeline.confirm_fixture_step(principal, reviewed, now_ms=now,
                                      idempotency_key="blocked", confirmed=True)
    assert session.pending is None
    assert world.turn == (1 if scenario == "world_advanced" else 0)


@pytest.mark.parametrize("mutation", ["draft", "wrong_profile", "no_rule"])
def test_unverified_knowledge_never_becomes_action(mutation):
    import json
    obj = json.loads(FIXTURE.read_text())
    if mutation == "draft":
        obj["status"] = "draft"
    if mutation == "wrong_profile":
        obj["profile"] = "unverified-game"
    if mutation == "no_rule":
        obj["rules"] = []
    raw = json.dumps(obj).encode()
    pipeline, world, session, principal, _ = setup_pipeline(change_pack=raw)
    reviewed = pipeline.review(now_ms=1000)
    assert reviewed.evaluation.status in ("unvalidated_pack", "profile_mismatch", "empty")
    with pytest.raises(ValueError, match="RECOMMENDATION_UNAVAILABLE"):
        pipeline.confirm_fixture_step(principal, reviewed, now_ms=1000,
                                      idempotency_key="blocked", confirmed=True)
    assert world.turn == 0 and session.pending is None


def test_revocation_after_review_is_checked_again(tmp_path):
    pipeline, world, session, principal, registry = setup_pipeline(registry=tmp_path)
    reviewed = pipeline.review(now_ms=1000)
    registry.revoke(reviewed.pack_digest)
    with pytest.raises(ValueError, match="RECOMMENDATION_UNAVAILABLE"):
        pipeline.confirm_fixture_step(principal, reviewed, now_ms=1001,
                                      idempotency_key="blocked", confirmed=True)
    assert world.turn == 0 and session.pending is None


def test_entitlement_revoked_after_review_still_denies_delivery():
    grants = ["offline-game-test"]
    pipeline, world, session, principal, _ = setup_pipeline(entitlements=lambda _: tuple(grants))
    reviewed = pipeline.review(now_ms=1000)
    grants.clear()
    with pytest.raises(ValueError):
        pipeline.confirm_fixture_step(principal, reviewed, now_ms=1001,
                                      idempotency_key="blocked", confirmed=True)
    assert world.turn == 0 and session.pending is None


def test_unobserved_outcome_latches_stop_and_never_repeats():
    pipeline, world, session, principal, _ = setup_pipeline(fault="missing_outcome")
    reviewed = pipeline.review(now_ms=1000)
    result = pipeline.confirm_fixture_step(principal, reviewed, now_ms=1000,
                                           idempotency_key="unknown-step", confirmed=True)
    assert result.outcome == "UNKNOWN" and session.stopped and world.turn == 1
    with pytest.raises(ValueError):
        pipeline.confirm_fixture_step(principal, reviewed, now_ms=1001,
                                      idempotency_key="unknown-step-2", confirmed=True)
    assert world.turn == 1


def test_no_cross_game_adapter_can_be_substituted():
    pipeline, world, session, _, _ = setup_pipeline()
    with pytest.raises(ValueError, match="OFFLINE_FIXTURE_ONLY"):
        OfflineTurnPipeline(object(), session, pipeline.knowledge)
    with pytest.raises(ValueError, match="OFFLINE_FIXTURE_ONLY"):
        OfflineTurnPipeline(TurnWorld("another-session"), session, pipeline.knowledge)

def test_forged_review_snapshot_and_recommendation_are_rejected():
    pipeline, world, session, principal, _ = setup_pipeline()
    original = pipeline.review(now_ms=1000)
    forged = replace(original, observation=replace(original.observation, turn=2))
    with pytest.raises(ValueError, match="REVIEW_TAMPERED"):
        pipeline.confirm_fixture_step(principal, forged, now_ms=1000,
                                      idempotency_key="forged-state", confirmed=True)
    fabricated = replace(original, evaluation=replace(original.evaluation, status="ready", items=()))
    with pytest.raises(ValueError, match="RECOMMENDATION_UNAVAILABLE"):
        pipeline.confirm_fixture_step(principal, fabricated, now_ms=1000,
                                      idempotency_key="forged-recommendation", confirmed=True)
    assert world.turn == 0 and session.pending is None
