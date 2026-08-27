from concurrent.futures import ThreadPoolExecutor

from app.core.integrity import (
    IntegrityNonceStore,
    IntegrityTier,
    authorize_for_tier,
    classify_verdicts,
)


def test_tier_policy_is_deterministic():
    assert classify_verdicts({"MEETS_STRONG_INTEGRITY"}) is IntegrityTier.STRONG
    assert classify_verdicts({"MEETS_DEVICE_INTEGRITY"}) is IntegrityTier.DEVICE
    assert classify_verdicts({"MEETS_BASIC_INTEGRITY"}) is IntegrityTier.BASIC
    assert classify_verdicts(set()) is IntegrityTier.UNKNOWN
    assert classify_verdicts({"MEETS_VIRTUAL_INTEGRITY"}) is IntegrityTier.FAILED
    assert authorize_for_tier(IntegrityTier.STRONG, "device:rotate")
    assert not authorize_for_tier(IntegrityTier.DEVICE, "device:rotate")
    assert authorize_for_tier(IntegrityTier.DEVICE, "game:read")
    assert authorize_for_tier(IntegrityTier.BASIC, "character:read")
    assert not authorize_for_tier(IntegrityTier.BASIC, "event:write")
    assert not authorize_for_tier(IntegrityTier.FAILED, "game:read")
    assert not authorize_for_tier(IntegrityTier.UNKNOWN, "game:read")


def test_nonce_replay_is_rejected():
    store = IntegrityNonceStore()
    nonce = store.issue()
    assert store.consume(nonce) is True
    assert store.consume(nonce) is False
    assert store.consume("not-issued") is False


def test_concurrent_nonce_consume_succeeds_once():
    store = IntegrityNonceStore()
    nonce = store.issue()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.consume(nonce), range(8)))
    assert results.count(True) == 1
    assert results.count(False) == 7
