from datetime import datetime, timedelta, timezone

from sentinel_core.security import AuthzContext, AuthorizationEngine, Policy, ReplayGuard


def test_authorization_is_default_deny():
    engine = AuthorizationEngine((Policy("character.read", frozenset({"user"}), frozenset({"character:read"})),))
    assert not engine.authorize(AuthzContext(None, None, frozenset({"user"}), frozenset({"character:read"}), frozenset()), "anonymous must deny")
    assert not engine.authorize(AuthzContext("u", None, frozenset(), frozenset({"character:read"}), frozenset()))
    assert not engine.authorize(AuthzContext("u", None, frozenset({"user"}), frozenset(), frozenset()))
    assert not engine.authorize(AuthzContext("u", None, frozenset({"user"}), frozenset({"character:read"}), frozenset()), "unknown resource policy is never inferred")
    assert engine.authorize(AuthzContext("u", None, frozenset({"user"}), frozenset({"character:read"}), frozenset()), "valid policy should allow")


def test_unknown_action_denies():
    engine = AuthorizationEngine(())
    ctx = AuthzContext("u", None, frozenset({"admin"}), frozenset({"*"}), frozenset({"*"}))
    assert not engine.authorize(ctx, "anything.unknown")


def test_nonce_can_only_be_consumed_once():
    guard = ReplayGuard()
    expires = datetime.now(timezone.utc) + timedelta(seconds=10)
    assert guard.verify_and_consume("n1", expires)
    assert not guard.verify_and_consume("n1", expires)


def test_expired_nonce_denies():
    guard = ReplayGuard()
    expires = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert not guard.verify_and_consume("n2", expires)
