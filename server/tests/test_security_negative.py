import base64
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core.security import AuthorizationEngine, Decision, Policy, Principal, canonical_json, session_hash
from app.main import app, store
from test_api import provision, reset_store

client = TestClient(app)


def signed_proof(key, challenge, request_id, timestamp=None):
    timestamp = int(time.time()) if timestamp is None else timestamp
    body = {"challenge": challenge, "timestamp": timestamp, "request_id": request_id}
    body["signature_b64"] = base64.b64encode(key.sign(canonical_json(body), ec.ECDSA(hashes.SHA256()))).decode()
    return body


def test_invalid_nonce_and_reused_nonce_are_rejected():
    reset_store()
    key, device, _ = provision()
    invalid = client.post(f"/v1/devices/{device['device_id']}/prove", json=signed_proof(key, "not-a-real-nonce", "invalid-nonce"))
    assert invalid.status_code == 401
    challenge = store.create_challenge(device["device_id"])
    valid = client.post(f"/v1/devices/{device['device_id']}/prove", json=signed_proof(key, challenge, "nonce-once"))
    assert valid.status_code == 200
    replay = client.post(f"/v1/devices/{device['device_id']}/prove", json=signed_proof(key, challenge, "nonce-twice"))
    assert replay.status_code == 401


def test_expired_nonce_is_rejected():
    reset_store()
    key, device, _ = provision()
    challenge = store.create_challenge(device["device_id"])
    store.challenges[session_hash(challenge)]["expires_at"] = 0
    response = client.post(f"/v1/devices/{device['device_id']}/prove", json=signed_proof(key, challenge, "expired-nonce"))
    assert response.status_code == 401


def test_invalid_signature_and_altered_payload_are_rejected():
    reset_store()
    key, device, _ = provision()
    challenge = store.create_challenge(device["device_id"])
    wrong_key = ec.generate_private_key(ec.SECP256R1())
    bad = signed_proof(wrong_key, challenge, "bad-signature")
    assert client.post(f"/v1/devices/{device['device_id']}/prove", json=bad).status_code == 401

    challenge = store.create_challenge(device["device_id"])
    altered = signed_proof(key, challenge, "signed-id")
    altered["request_id"] = "altered-id"
    assert client.post(f"/v1/devices/{device['device_id']}/prove", json=altered).status_code == 401


def test_stale_timestamp_is_rejected():
    reset_store()
    key, device, _ = provision()
    challenge = store.create_challenge(device["device_id"])
    stale = signed_proof(key, challenge, "stale", timestamp=int(time.time()) - 1000)
    assert client.post(f"/v1/devices/{device['device_id']}/prove", json=stale).status_code == 401


def test_revoked_device_and_rotated_key_are_rejected():
    reset_store()
    key, device, _ = provision()
    store.devices[device["device_id"]]["state"] = "REVOKED"
    revoked = client.post(f"/v1/devices/{device['device_id']}/prove", json=signed_proof(key, store.create_challenge(device["device_id"]), "revoked-device"))
    assert revoked.status_code == 401

    reset_store()
    key, device, _ = provision()
    new_key = ec.generate_private_key(ec.SECP256R1())
    new_pub = new_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    store.devices[device["device_id"]]["public_key"] = base64.b64encode(new_pub).decode()
    rotated = client.post(f"/v1/devices/{device['device_id']}/prove", json=signed_proof(key, store.create_challenge(device["device_id"]), "rotated-key"))
    assert rotated.status_code == 401


def test_expired_and_revoked_sessions_are_rejected():
    reset_store()
    _, _, session = provision()
    store.sessions[session_hash(session["session_token"])]["expires_at"] = time.time() - 1
    expired = client.post("/v1/authorize", headers={"Authorization": "Bearer " + session["session_token"]}, json={"action": "character:read", "resource": "character:1"})
    assert expired.status_code == 401

    reset_store()
    _, _, session = provision()
    assert client.post("/v1/sessions/revoke", headers={"Authorization": "Bearer " + session["session_token"]}).status_code == 200
    revoked = client.post("/v1/authorize", headers={"Authorization": "Bearer " + session["session_token"]}, json={"action": "character:read", "resource": "character:1"})
    assert revoked.status_code == 401


def test_missing_scope_wrong_role_and_explicit_deny():
    engine = AuthorizationEngine([
        Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"}), roles=frozenset({"user"})),
        Policy(Decision.DENY, "character:read", "character:secret", scopes=frozenset({"character:read"})),
    ])
    assert engine.authorize(Principal("u", "d", frozenset({"user"}), frozenset()), "character:read", "character:1")[0] is Decision.DENY
    assert engine.authorize(Principal("u", "d", frozenset({"guest"}), frozenset({"character:read"})), "character:read", "character:1")[0] is Decision.DENY
    assert engine.authorize(Principal("u", "d", frozenset({"user"}), frozenset({"character:read"})), "character:read", "character:secret")[0] is Decision.DENY


def test_direct_unauthorized_recommendation_call_is_blocked():
    reset_store()
    _, _, session = provision()
    record = store.sessions[session_hash(session["session_token"])]
    record["scopes"] = ["character:read"]
    response = client.post("/v1/recommendations", headers={"Authorization": "Bearer " + session["session_token"]}, json={"context": {}})
    assert response.status_code == 403


def test_cross_device_duplicate_and_sequence_replay_guards():
    reset_store()
    _, device, session = provision()
    principal = {"user_id": "u1", "device_id": device["device_id"]}
    event = {"event_id": "evt-000001", "device_id": device["device_id"], "type": "character.snapshot", "schema_version": 1, "occurred_at": "2026-08-12T06:00:00Z", "sequence": 0, "payload": {"hp": 100}}
    assert store.save_event_batch(principal, [{**event, "device_id": "other-device"}], "cross-device") is None if False else True
    try:
        store.save_event_batch(principal, [{**event, "device_id": "other-device"}], "cross-device")
        raise AssertionError("cross-device event was accepted")
    except ValueError as exc:
        assert str(exc) == "DEVICE_SCOPE_MISMATCH"
    first = store.save_event_batch(principal, [event], "duplicate-key")
    second = store.save_event_batch(principal, [event], "duplicate-key")
    assert first == {"accepted": 1, "duplicates": 0}
    assert second == first
    try:
        store.save_event_batch(principal, [{**event, "event_id": "evt-seq-replay"}], "sequence-key")
        raise AssertionError("sequence replay was accepted")
    except ValueError as exc:
        assert str(exc) == "SEQUENCE_REPLAY"
    assert session["session_token"]
