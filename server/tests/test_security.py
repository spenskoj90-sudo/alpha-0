from app.core.security import AuthorizationEngine, Decision, Policy, Principal, ScopeEngine, canonical_json, fresh_request_timestamp


def principal(*, roles=(), scopes=()):
    return Principal("u1", "d1", frozenset(roles), frozenset(scopes))


def test_default_deny():
    engine = AuthorizationEngine([])
    assert engine.authorize(principal(), "character:read", "character:1") == (Decision.DENY, "NO_MATCHING_POLICY")


def test_scope_allows():
    engine = AuthorizationEngine([Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"}))])
    assert engine.authorize(principal(scopes=("character:read",)), "character:read", "character:1")[0] is Decision.ALLOW
    assert engine.authorize(principal(), "character:read", "character:1")[0] is Decision.DENY


def test_deny_wins():
    engine = AuthorizationEngine([
        Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
        Policy(Decision.DENY, "character:read", "character:secret", scopes=frozenset({"character:read"})),
    ])
    assert engine.authorize(principal(scopes=("character:read",)), "character:read", "character:secret")[0] is Decision.DENY


def test_invalid_authorization_input_denied():
    engine = AuthorizationEngine([Policy(Decision.ALLOW, "*", "*")])
    assert engine.authorize(principal(), "", "x")[0] is Decision.DENY
    assert engine.authorize(principal(), "x" * 201, "x")[0] is Decision.DENY


def test_scope_validation_and_composition():
    assert ScopeEngine.compose(["game:read", "game:write"], ["game:read"]) == frozenset({"game:read"})
    try:
        ScopeEngine.compose(["game:read"], ["game:admin"])
        assert False
    except ValueError as exc:
        assert str(exc) == "SCOPE_NOT_GRANTED"


def test_canonical_json_is_stable():
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_timestamp_window():
    assert fresh_request_timestamp(1000, now=1000)
    assert not fresh_request_timestamp(700, now=1000)
