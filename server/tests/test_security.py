from app.core.security import AuthorizationEngine, Decision, Policy, Principal, canonical_json, fresh_request_timestamp


def principal(*, roles=(), scopes=()):
    return Principal("u1", "d1", frozenset(roles), frozenset(scopes))


def test_default_deny():
    engine = AuthorizationEngine([Policy(Decision.DENY, "*", "*")])
    assert engine.authorize(principal(), "character:read", "character:1") == (Decision.DENY, "POLICY_DENY")


def test_scope_allows():
    engine = AuthorizationEngine([
        Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
        Policy(Decision.DENY, "*", "*"),
    ])
    assert engine.authorize(principal(scopes=("character:read",)), "character:read", "character:1")[0] is Decision.ALLOW
    assert engine.authorize(principal(), "character:read", "character:1")[0] is Decision.DENY


def test_deny_wins():
    engine = AuthorizationEngine([
        Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
        Policy(Decision.DENY, "character:read", "character:secret", scopes=frozenset({"character:read"})),
    ])
    assert engine.authorize(principal(scopes=("character:read",)), "character:read", "character:secret")[0] is Decision.DENY


def test_canonical_json_is_stable():
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_timestamp_window():
    assert fresh_request_timestamp(1000, now=1000)
    assert not fresh_request_timestamp(700, now=1000)
