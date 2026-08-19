from __future__ import annotations

from time import perf_counter

from app.core.security import AuthorizationEngine, Decision, Policy, Principal


def test_authorization_p99_regression_guard() -> None:
    engine = AuthorizationEngine([
        Policy(
            effect=Decision.ALLOW,
            action="character:read",
            resource="character:123",
            roles=frozenset({"user"}),
            scopes=frozenset({"character:read"}),
        )
    ])
    principal = Principal(
        user_id="perf-user",
        device_id="perf-device",
        roles=frozenset({"user"}),
        scopes=frozenset({"character:read"}),
    )

    samples: list[float] = []
    for _ in range(2000):
        start = perf_counter()
        decision, _ = engine.authorize(principal, "character:read", "character:123")
        samples.append((perf_counter() - start) * 1000)
        assert decision is Decision.ALLOW

    samples.sort()
    p99_ms = samples[int(len(samples) * 0.99)]
    assert p99_ms < 100.0


def test_event_ingestion_regression_guard() -> None:
    from app.core.store import MemoryStore

    store = MemoryStore()
    device_id = store.register_device("perf-user", "android", "key", "fp", "challenge")
    principal = {"user_id": "perf-user", "device_id": device_id}

    start = perf_counter()
    for sequence in range(250):
        store.save_event_batch(
            principal,
            [{
                "event_id": f"perf-{sequence}",
                "device_id": device_id,
                "type": "character.snapshot",
                "schema_version": 1,
                "occurred_at": "2026-08-12T00:00:00Z",
                "sequence": sequence,
                "payload": {"hp": 100},
            }],
            f"perf-key-{sequence}",
        )
    elapsed = perf_counter() - start
    throughput = 250 / elapsed if elapsed else float("inf")
    assert throughput > 100.0
