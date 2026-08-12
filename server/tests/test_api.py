import base64
import hashlib
import json
import os
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

os.environ["SENTINEL_ENROLLMENT_TOKEN"] = "u1:secret"
os.environ["SENTINEL_REQUIRE_ENROLLMENT"] = "true"

from app.main import app, store

client = TestClient(app)


def reset_store():
    if hasattr(store, "devices"):
        store.devices.clear()
        store.challenges.clear()
        store.sessions.clear()
        store.events.clear()
        store.audit.clear()
        store.idempotency.clear()
        store.proof_requests.clear()
        store.entitlements.clear()
        store.failures.clear()


def provision():
    reset_store()
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    pub64 = base64.b64encode(pub).decode()
    fingerprint = hashlib.sha256(pub).hexdigest()
    reg = client.post("/v1/devices/register", headers={"X-Enrollment-Token": "u1:secret"}, json={"user_id": "u1", "platform": "android", "public_key_der_b64": pub64, "fingerprint_sha256": fingerprint})
    assert reg.status_code == 200
    device = reg.json()
    body = {"challenge": device["challenge"], "timestamp": int(time.time()), "request_id": "req-1"}
    signed = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    body["signature_b64"] = base64.b64encode(key.sign(signed, ec.ECDSA(hashes.SHA256()))).decode()
    proof = client.post(f"/v1/devices/{device['device_id']}/prove", json=body)
    assert proof.status_code == 200
    return key, device, proof.json()


def test_registration_requires_user_bound_enrollment():
    reset_store()
    response = client.post("/v1/devices/register", headers={"X-Enrollment-Token": "u2:secret"}, json={"user_id": "u1", "platform": "android", "public_key_der_b64": "bad", "fingerprint_sha256": "0" * 64})
    assert response.status_code == 422


def test_challenge_replay_is_rejected():
    key, device, session = provision()
    assert session["session_token"]
    body = {"challenge": device["challenge"], "timestamp": int(time.time()), "request_id": "replay", "signature_b64": "A" * 24}
    response = client.post(f"/v1/devices/{device['device_id']}/prove", json=body)
    assert response.status_code == 401
    assert key is not None


def test_refresh_rotation_and_replay_detection():
    _, _, session = provision()
    first = client.post("/v1/sessions/refresh", json={"refresh_token": session["refresh_token"]})
    assert first.status_code == 200
    replay = client.post("/v1/sessions/refresh", json={"refresh_token": session["refresh_token"]})
    assert replay.status_code == 401


def test_authorization_default_deny():
    _, _, session = provision()
    allowed = client.post("/v1/authorize", headers={"Authorization": "Bearer " + session["session_token"]}, json={"action": "character:read", "resource": "character:42"})
    denied = client.post("/v1/authorize", headers={"Authorization": "Bearer " + session["session_token"]}, json={"action": "admin:delete", "resource": "admin:system"})
    assert allowed.status_code == 200
    assert denied.status_code == 200
    assert denied.json()["decision"] == "DENY"


def test_event_batch_is_idempotent_and_rejects_key_reuse():
    _, device, session = provision()
    headers = {"Authorization": "Bearer " + session["session_token"], "Idempotency-Key": "batch-1"}
    payload = {"events": [{"event_id": "evt-000001", "device_id": device["device_id"], "type": "character.snapshot", "schema_version": 1, "occurred_at": "2026-08-12T06:00:00Z", "sequence": 0, "payload": {"hp": 100}}]}
    first = client.post("/v1/events:batch", headers=headers, json=payload)
    second = client.post("/v1/events:batch", headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"accepted": 1, "duplicates": 0}
    altered = {"events": [{**payload["events"][0], "payload": {"hp": 99}}]}
    conflict = client.post("/v1/events:batch", headers=headers, json=altered)
    assert conflict.status_code == 409


def test_security_headers_present():
    response = client.get("/healthz")
    assert response.status_code == 200
    for name in ["X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "Content-Security-Policy"]:
        assert name in response.headers


def test_session_revoke_blocks_access():
    _, _, session = provision()
    token = session["session_token"]
    revoked = client.post("/v1/sessions/revoke", headers={"Authorization": "Bearer " + token})
    assert revoked.status_code == 200
    denied = client.post("/v1/authorize", headers={"Authorization": "Bearer " + token}, json={"action": "character:read", "resource": "character:42"})
    assert denied.status_code == 401
