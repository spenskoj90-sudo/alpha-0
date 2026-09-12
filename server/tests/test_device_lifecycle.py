import base64
import hashlib
import json
import os
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from app.main import REFRESH_TTL_SECONDS, SESSION_TTL_SECONDS, app, store, user_store

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


def register(key):
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    public_b64 = base64.b64encode(public).decode()
    fingerprint = hashlib.sha256(public).hexdigest()
    response = client.post(
        "/v1/devices/register",
        headers={"X-Enrollment-Token": "u1:secret"},
        json={
            "user_id": "u1",
            "platform": "android",
            "public_key_der_b64": public_b64,
            "fingerprint_sha256": fingerprint,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def prove(key, device, request_id):
    body = {
        "challenge": device["challenge"],
        "timestamp": int(time.time()),
        "request_id": request_id,
    }
    signed = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    body["signature_b64"] = base64.b64encode(key.sign(signed, ec.ECDSA(hashes.SHA256()))).decode()
    response = client.post(f"/v1/devices/{device['device_id']}/prove", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def bind_with_session(key, user_id="u1"):
    access, refresh, _, _ = store.issue_session(None, user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    user_store.restrict_session_scopes(store, access, {"character:read", "game:read", "audit:read"})
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    response = client.post(
        "/v1/devices/bind",
        headers={"Authorization": "Bearer " + access},
        json={
            "platform": "android",
            "public_key_der_b64": base64.b64encode(public).decode(),
            "fingerprint_sha256": hashlib.sha256(public).hexdigest(),
        },
    )
    assert response.status_code == 200, response.text
    return access, refresh, response.json()


def event_payload(device_id, event_id="event-0001", sequence=0):
    return {
        "events": [
            {
                "event_id": event_id,
                "device_id": device_id,
                "type": "demo.event",
                "schema_version": 1,
                "occurred_at": "2026-09-12T00:00:00Z",
                "sequence": sequence,
                "payload": {"source": "android-proof-test"},
            }
        ]
    }


def test_device_rotate_invalidates_old_session_then_new_device_can_be_revoked():
    reset_store()
    old_key = ec.generate_private_key(ec.SECP256R1())
    old_device = register(old_key)
    old_session = prove(old_key, old_device, "old-proof")
    old_token = old_session["session_token"]

    new_key = ec.generate_private_key(ec.SECP256R1())
    new_public = new_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    new_public_b64 = base64.b64encode(new_public).decode()
    new_fingerprint = hashlib.sha256(new_public).hexdigest()

    rotated = client.post(
        f"/v1/devices/{old_device['device_id']}/rotate",
        headers={"Authorization": "Bearer " + old_token},
        json={
            "platform": "android",
            "public_key_der_b64": new_public_b64,
            "fingerprint_sha256": new_fingerprint,
        },
    )
    assert rotated.status_code == 200, rotated.text
    new_device = rotated.json()
    assert new_device["device_id"] != old_device["device_id"]
    assert new_device["state"] == "ACTIVE"

    old_access_after_rotate = client.post(
        "/v1/authorize",
        headers={"Authorization": "Bearer " + old_token},
        json={"action": "character:read", "resource": "character:42"},
    )
    assert old_access_after_rotate.status_code == 401

    new_session = prove(new_key, new_device, "new-proof")
    new_token = new_session["session_token"]
    new_access_before_revoke = client.post(
        "/v1/authorize",
        headers={"Authorization": "Bearer " + new_token},
        json={"action": "character:read", "resource": "character:42"},
    )
    assert new_access_before_revoke.status_code == 200
    assert new_access_before_revoke.json()["decision"] == "ALLOW"

    revoked = client.post(
        f"/v1/devices/{new_device['device_id']}/revoke",
        headers={"Authorization": "Bearer " + new_token},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json() == {"revoked": True}

    new_access_after_revoke = client.post(
        "/v1/authorize",
        headers={"Authorization": "Bearer " + new_token},
        json={"action": "character:read", "resource": "character:42"},
    )
    assert new_access_after_revoke.status_code == 401

    old_access_after_revoke = client.post(
        "/v1/authorize",
        headers={"Authorization": "Bearer " + old_token},
        json={"action": "character:read", "resource": "character:42"},
    )
    assert old_access_after_revoke.status_code == 401


def test_bound_read_session_cannot_ingest_until_device_proof_issues_write_session():
    reset_store()
    key = ec.generate_private_key(ec.SECP256R1())
    read_access, _, bound = bind_with_session(key)
    device_id = bound["device_id"]

    denied = client.post(
        "/v1/events:batch",
        headers={
            "Authorization": "Bearer " + read_access,
            "Idempotency-Key": "pre-proof-batch",
        },
        json=event_payload(device_id),
    )
    assert denied.status_code == 403

    proof = prove(key, bound, "android-proof")
    assert "game:write" in proof["scopes"]

    accepted = client.post(
        "/v1/events:batch",
        headers={
            "Authorization": "Bearer " + proof["session_token"],
            "Idempotency-Key": "post-proof-batch",
        },
        json=event_payload(device_id),
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json() == {"accepted": 1, "duplicates": 0}


def test_authenticated_owner_can_refresh_consumed_device_proof_challenge():
    reset_store()
    key = ec.generate_private_key(ec.SECP256R1())
    read_access, _, bound = bind_with_session(key)
    first_challenge = bound["challenge"]

    first_proof = prove(key, bound, "first-proof")
    assert first_proof["session_token"]

    refreshed = client.post(
        f"/v1/devices/{bound['device_id']}/challenge",
        headers={"Authorization": "Bearer " + read_access},
    )
    assert refreshed.status_code == 200, refreshed.text
    second_challenge = refreshed.json()["challenge"]
    assert second_challenge
    assert second_challenge != first_challenge

    second_proof = prove(
        key,
        {"device_id": bound["device_id"], "challenge": second_challenge},
        "second-proof",
    )
    assert "game:write" in second_proof["scopes"]


def test_foreign_session_cannot_refresh_device_challenge():
    reset_store()
    key = ec.generate_private_key(ec.SECP256R1())
    _, _, bound = bind_with_session(key, user_id="u1")
    foreign_access, _, _, _ = store.issue_session(None, "u2", SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)

    denied = client.post(
        f"/v1/devices/{bound['device_id']}/challenge",
        headers={"Authorization": "Bearer " + foreign_access},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "DEVICE_SCOPE_MISMATCH"
