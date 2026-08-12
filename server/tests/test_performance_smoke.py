from time import perf_counter

from app.core.security import AuthorizationEngine, Decision, Policy, Principal


def test_authorization_performance_smoke():
    engine = AuthorizationEngine([
        Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
        Policy(Decision.DENY, "*", "*"),
    ])
    principal = Principal("u", "d", frozenset({"user"}), frozenset({"character:read"}))

    start = perf_counter()
    for _ in range(5000):
        assert engine.authorize(principal, "character:read", "character:1")[0] is Decision.ALLOW
    elapsed = perf_counter() - start

    # This is a smoke budget, not a benchmark claim.
    assert elapsed < 1.0
