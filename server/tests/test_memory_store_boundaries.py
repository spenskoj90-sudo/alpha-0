from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.p1_runtime import BillingState
from app.core.security import session_hash
from app.core.store import MemoryStore, event_hash_payload


def _device(store: MemoryStore, user: str = "user-1", *, key="public-key", fp="a" * 64) -> str:
    return store.register_device(user, "android", key, fp, f"challenge-{uuid.uuid4().hex}")


def _event(device_id: str, sequence: int, event_id: str | None = None, request_id: str | None = None):
    return {
        "event_id": event_id or f"evt-{sequence}-{uuid.uuid4().hex}",
        "device_id": device_id,
        "sequence": sequence,
        "event_type": "test.event",
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": {"value": sequence},
        "request_id": request_id,
    }


def test_event_hash_ignores_transport_request_id_but_not_durable_intent() -> None:
    first = _event("device", 1, "evt-stable", "req-a")
    second = {**first, "request_id": "req-b"}
    assert event_hash_payload([first]) == event_hash_payload([second])
    assert event_hash_payload([first]) != event_hash_payload([{**second, "sequence": 2}])


def test_device_registration_is_idempotent_for_exact_owner_key_and_fail_closed_otherwise() -> None:
    store = MemoryStore()
    first = _device(store)
    second = store.register_device("user-1", "android", "public-key", "A" * 64, "second-challenge")
    assert second == first

    with pytest.raises(ValueError, match="DEVICE_KEY_CONFLICT"):
        store.register_device("user-2", "android", "public-key", "a" * 64, "foreign")
    with pytest.raises(ValueError, match="DEVICE_KEY_CONFLICT"):
        store.register_device("user-1", "android", "different-key", "a" * 64, "changed")

    store.devices[first]["state"] = "REVOKED"
    with pytest.raises(ValueError, match="DEVICE_KEY_CONFLICT"):
        store.register_device("user-1", "android", "public-key", "a" * 64, "revoked")


def test_device_touch_and_key_lookup_require_active_exact_binding() -> None:
    store = MemoryStore()
    device = _device(store)
    assert store.touch_device("missing") is False
    assert store.find_active_device_by_key("wrong", "a" * 64) is None
    found = store.find_active_device_by_key("public-key", "A" * 64)
    assert found and found["device_id"] == device
    assert store.touch_device(device) is True
    assert store.devices[device]["last_seen_at"] is not None
    store.devices[device]["state"] = "REVOKED"
    assert store.touch_device(device) is False
    assert store.find_active_device_by_key("public-key", "a" * 64) is None


def test_device_rotation_validates_owner_state_conflicts_and_can_reuse_exact_new_binding() -> None:
    store = MemoryStore()
    old = _device(store, fp="1" * 64)
    old_access, _, _, _ = store.issue_session(old, "user-1", 60, 120)

    with pytest.raises(ValueError, match="DEVICE_NOT_ACTIVE"):
        store.rotate_device_identity("missing", "user-1", "android", "new", "2" * 64, "c", 60, 120)
    with pytest.raises(ValueError, match="DEVICE_NOT_ACTIVE"):
        store.rotate_device_identity(old, "foreign", "android", "new", "2" * 64, "c", 60, 120)

    foreign = _device(store, "foreign", key="foreign-key", fp="2" * 64)
    with pytest.raises(ValueError, match="DEVICE_KEY_CONFLICT"):
        store.rotate_device_identity(old, "user-1", "android", "foreign-key", "2" * 64, "c", 60, 120)
    assert store.devices[foreign]["state"] == "ACTIVE"

    reusable = _device(store, "user-1", key="new-key", fp="3" * 64)
    new_id, access, refresh, _, scopes = store.rotate_device_identity(
        old, "user-1", "android", "new-key", "3" * 64, "rotation", 60, 120
    )
    assert new_id == reusable
    assert access and refresh and scopes
    assert store.devices[old]["state"] == "REVOKED"
    assert store.get_session(old_access) is None
    assert store.get_session(access)["device_id"] == reusable


def test_challenge_and_proof_replay_guards_cover_mismatch_expiry_and_consumption() -> None:
    store = MemoryStore()
    device = _device(store)
    challenge = store.create_challenge(device)
    assert store.consume_challenge("missing", device) is False
    assert store.consume_challenge(challenge, "other") is False
    digest = session_hash(challenge)
    store.challenges[digest]["expires_at"] = time.time() - 1
    assert store.consume_challenge(challenge, device) is False

    fresh = store.create_challenge(device)
    assert store.consume_challenge(fresh, device) is True
    assert store.consume_challenge(fresh, device) is False

    assert store.consume_proof_request(device, "request-1") is True
    assert store.consume_proof_request(device, "request-1") is False


def test_session_read_rotation_and_revocation_fail_closed_for_every_stale_state() -> None:
    store = MemoryStore()
    device = _device(store)

    access, refresh, _, _ = store.issue_session(device, "user-1", 60, 120)
    assert store.get_session(access) is not None
    assert store.get_session("missing") is None

    record = store.sessions[session_hash(access)]
    record["expires_at"] = time.time() - 1
    assert store.get_session(access) is None
    record["expires_at"] = time.time() + 60
    record["revoked"] = True
    assert store.get_session(access) is None

    access2, refresh2, _, _ = store.issue_session(device, "user-1", 60, 120)
    store.devices.pop(device)
    assert store.get_session(access2) is None
    assert store.rotate_refresh(refresh2, 60, 120) is None

    device = _device(store, key="key-2", fp="b" * 64)
    access3, refresh3, _, _ = store.issue_session(device, "user-1", 60, 120)
    store.devices[device]["state"] = "REVOKED"
    assert store.get_session(access3) is None
    assert store.rotate_refresh(refresh3, 60, 120) is None

    user_access, user_refresh, _, _ = store.issue_session(None, "user-1", 60, 120)
    assert store.rotate_refresh("missing", 60, 120) is None
    user_record = store.sessions[session_hash(user_access)]
    user_record["refresh_expires_at"] = time.time() - 1
    assert store.rotate_refresh(user_refresh, 60, 120) is None
    user_record["refresh_expires_at"] = time.time() + 120
    user_record["refresh_used"] = True
    assert store.rotate_refresh(user_refresh, 60, 120) is None

    fresh_access, fresh_refresh, _, _ = store.issue_session(None, "user-1", 60, 120)
    rotated = store.rotate_refresh(fresh_refresh, 60, 120)
    assert rotated is not None
    assert store.get_session(fresh_access) is None

    assert store.revoke_session("missing") is False
    new_access = rotated[0]
    assert store.revoke_session(new_access) is True
    assert store.revoke_session(new_access) is False


def test_event_batch_enforces_device_scope_sequence_idempotency_and_duplicate_semantics() -> None:
    store = MemoryStore()
    device = _device(store)
    principal = {"user_id": "user-1", "device_id": device}

    first = _event(device, 0, "evt-0")
    assert store.save_event_batch(principal, [first], "key-1") == {"accepted": 1, "duplicates": 0}
    assert store.save_event_batch(principal, [{**first, "request_id": "other"}], "key-1") == {
        "accepted": 1,
        "duplicates": 0,
    }
    with pytest.raises(ValueError, match="IDEMPOTENCY_KEY_REUSE"):
        store.save_event_batch(principal, [{**first, "payload": {"changed": True}}], "key-1")

    assert store.save_event_batch(principal, [first], None) == {"accepted": 0, "duplicates": 1}

    with pytest.raises(ValueError, match="DEVICE_NOT_FOUND"):
        store.save_event_batch({"user_id": "user-1", "device_id": "missing"}, [_event("missing", 1)], None)
    with pytest.raises(ValueError, match="DEVICE_SCOPE_MISMATCH"):
        store.save_event_batch(principal, [_event("foreign-device", 1)], None)

    duplicate_sequence = [_event(device, 1, "evt-a"), _event(device, 1, "evt-b")]
    with pytest.raises(ValueError, match="SEQUENCE_REPLAY"):
        store.save_event_batch(principal, duplicate_sequence, None)
    with pytest.raises(ValueError, match="SEQUENCE_REPLAY"):
        store.save_event_batch(principal, [_event(device, 0, "evt-old")], None)

    ordered = [_event(device, 2, "evt-2"), _event(device, 1, "evt-1")]
    assert store.save_event_batch(principal, ordered, None) == {"accepted": 2, "duplicates": 0}
    assert store.devices[device]["last_sequence"] == 2


def test_audit_security_failures_and_entitlement_filters_are_owner_scoped(monkeypatch) -> None:
    store = MemoryStore()
    store.add_audit({"actor_user_id": "u1", "action": "one"})
    store.add_audit({"actor_user_id": "u2", "action": "two"})
    assert [item["action"] for item in store.get_audit("u1")] == ["one"]

    now = time.time()
    store.failures = [("u1", now - 901), ("u1", now - 10), ("u2", now - 10)]
    assert store.security_failure_count("u1") == 1
    assert store.record_security_failure("u1", "test") == 2

    store.create_entitlement({"user_id": "u1", "game_id": "wow"})
    store.create_entitlement({"user_id": "u2", "game_id": "diablo"})
    assert len(store.list_entitlements()) == 2
    assert store.list_entitlements("u1") == [{"user_id": "u1", "game_id": "wow"}]


def _subscription_item(user="u1", provider_id=None):
    now = datetime.now(UTC)
    return {
        "user_id": user,
        "plan_code": "core-plus",
        "currency": "USD",
        "provider": "stripe",
        "provider_subscription_id": provider_id,
        "status": "PENDING",
        "started_at": now,
        "expires_at": None,
    }


def test_subscription_binding_transition_and_event_storage_fail_closed() -> None:
    store = MemoryStore()
    first = store.create_subscription(_subscription_item(provider_id="sub-1"))
    with pytest.raises(ValueError, match="SUBSCRIPTION_ALREADY_EXISTS"):
        store.create_subscription(_subscription_item("u2", "sub-1"))

    assert store.get_subscription("missing") is None
    assert store.find_subscription_by_provider_id("stripe", "missing") is None
    assert store.list_subscriptions("u2") == []

    for bad in ("", "x" * 257):
        with pytest.raises(ValueError, match="INVALID_PROVIDER_SUBSCRIPTION_ID"):
            store.bind_subscription_provider_id(first["id"], "stripe", bad)
    with pytest.raises(ValueError, match="SUBSCRIPTION_NOT_FOUND"):
        store.bind_subscription_provider_id("missing", "stripe", "sub-2")
    with pytest.raises(ValueError, match="SUBSCRIPTION_PROVIDER_MISMATCH"):
        store.bind_subscription_provider_id(first["id"], "other", "sub-2")

    second = store.create_subscription(_subscription_item("u2"))
    assert store.bind_subscription_provider_id(second["id"], "stripe", "sub-2")["provider_subscription_id"] == "sub-2"

    event = SimpleNamespace(
        event_id="billing-1",
        provider="stripe",
        target_state=BillingState.ACTIVE,
        occurred_at=datetime.now(UTC),
    )
    active = store.apply_subscription_transition(second["id"], event, "PENDING", "ACTIVE")
    assert active["status"] == "ACTIVE"
    assert active["expires_at"] is None
    assert store.bind_subscription_provider_id(second["id"], "stripe", "sub-2")["status"] == "ACTIVE"
    with pytest.raises(ValueError, match="SUBSCRIPTION_STATE_CHANGED"):
        store.bind_subscription_provider_id(second["id"], "stripe", "different")

    canceled_event = SimpleNamespace(**{**event.__dict__, "occurred_at": datetime.now(UTC) + timedelta(seconds=1)})
    canceled = store.apply_subscription_transition(second["id"], canceled_event, "ACTIVE", "CANCELED")
    assert canceled["expires_at"] == canceled_event.occurred_at

    assert store.has_billing_event("billing-1") is False
    store.record_billing_event(event, second["id"])
    assert store.has_billing_event("billing-1") is True
    with pytest.raises(ValueError, match="BILLING_EVENT_DUPLICATE"):
        store.record_billing_event(event, second["id"])


def test_character_upsert_is_unique_per_user_game_external_identity_and_bounds_state_shape() -> None:
    store = MemoryStore()
    first = store.upsert_character(
        {
            "user_id": "u1",
            "game_id": "wow",
            "external_id": "char-1",
            "name": "First",
            "state_json": "not-a-dict",
        }
    )
    assert first["state_json"] == {}
    assert store.get_character(first["id"]) == first
    assert store.get_character("missing") is None
    assert store.list_characters("u2") == []

    replacement = store.upsert_character(
        {
            "id": "different-id",
            "user_id": "u1",
            "game_id": "wow",
            "external_id": "char-1",
            "name": "Updated",
            "version": 2,
            "state_json": {"level": 80},
            "updated_at": "2026-09-25T00:00:00Z",
        }
    )
    assert replacement["id"] == first["id"]
    assert replacement["name"] == "Updated"
    assert store.list_characters("u1") == [replacement]
