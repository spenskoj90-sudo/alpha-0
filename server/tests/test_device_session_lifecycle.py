import base64
import hashlib
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "false")

from app.main import REFRESH_TTL_SECONDS, SESSION_TTL_SECONDS, app, store

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


def public_material(key):
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(public).decode(), hashlib.sha256(public).hexdigest()


def session_for(user_id="u1"):
    access, refresh, _, _ = store.issue_session(None, user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    return access, refresh


def test_bind_links_existing_user_session_to_device():
    reset_store()
    key = ec.generate_private_key(ec.SECP256R1())
    public_b64, fingerprint = public_material(key)
    access, _ = session_for()

    response = client.post(
        "/v1/devices/bind",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "platform": "android",
            "public_key_der_b64": public_b64,
            "fingerprint_sha256": fingerprint,
        },
    )

    assert response.status_code == 200, response.text
    device_id = response.json()["device_id"]
    assert store.get_session(access)["device_id"] == device_id


def test_rotate_rejects_foreign_device_and_bad_fingerprint_and_replaces_session():
    reset_store()
    owner_key = ec.generate_private_key(ec.SECP256R1())
    owner_public_b64, owner_fingerprint = public_material(owner_key)
    owner_device = store.register_device("u1", "android", owner_public_b64, owner_fingerprint, "unused-owner")
    owner_access, _ = session_for()
    store.sessions[hashlib.sha256(owner_access.encode()).hexdigest()]["device_id"] = owner_device

    foreign_key = ec.generate_private_key(ec.SECP256R1())
    foreign_public_b64, foreign_fingerprint = public_material(foreign_key)
    foreign_device = store.register_device("u2", "android", foreign_public_b64, foreign_fingerprint, "unused-foreign")

    foreign_attempt = client.post(
        f"/v1/devices/{foreign_device}/rotate",
        headers={"Authorization": f"Bearer {owner_access}"},
        json={
            "platform": "android",
            "public_key_der_b64": foreign_public_b64,
            "fingerprint_sha256": foreign_fingerprint,
        },
    )
    assert foreign_attempt.status_code == 403
    assert foreign_attempt.json()["code"] == "DEVICE_SCOPE_MISMATCH"

    new_key = ec.generate_private_key(ec.SECP256R1())
    new_public_b64, new_fingerprint = public_material(new_key)
    bad_fingerprint = "0" * 64
    bad = client.post(
        f"/v1/devices/{owner_device}/rotate",
        headers={"Authorization": f"Bearer {owner_access}"},
        json={
            "platform": "android",
            "public_key_der_b64": new_public_b64,
            "fingerprint_sha256": bad_fingerprint,
        },
    )
    assert bad.status_code == 400
    assert bad.json()["code"] == "FINGERPRINT_MISMATCH"

    rotated = client.post(
        f"/v1/devices/{owner_device}/rotate",
        headers={"Authorization": f"Bearer {owner_access}"},
        json={
            "platform": "android",
            "public_key_der_b64": new_public_b64,
            "fingerprint_sha256": new_fingerprint,
        },
    )
    assert rotated.status_code == 200
    payload = rotated.json()
    assert "device_id" in payload
    assert payload["device_id"] != owner_device
    assert "state" in payload
    assert payload["state"] == "ACTIVE"
    assert "session_token" in payload
    assert payload["session_token"]
    assert "refresh_token" in payload
    assert payload["refresh_token"]
    assert store.get_session(owner_access) is None

    new_access = payload["session_token"]
    authorized = client.post(
        "/v1/authorize",
        headers={"Authorization": f"Bearer {new_access}"},
        json={"action": "character:read", "resource": "character:42"},
    )
    assert authorized.status_code == 200
    assert store.get_session(new_access)["device_id"] == payload["device_id"]


def test_revoke_rejects_foreign_device_and_revokes_all_device_sessions():
    reset_store()
    owner_key = ec.generate_private_key(ec.SECP256R1())
    owner_public_b64, owner_fingerprint = public_material(owner_key)
    owner_device = store.register_device("u1", "android", owner_public_b64, owner_fingerprint, "unused-owner")
    owner_access, _ = session_for()
    store.sessions[hashlib.sha256(owner_access.encode()).hexdigest()]["device_id"] = owner_device

    second_access, _ = session_for()
    store.sessions[hashlib.sha256(second_access.encode()).hexdigest()]["device_id"] = owner_device

    foreign_key = ec.generate_private_key(ec.SECP256R1())
    foreign_public_b64, foreign_fingerprint = public_material(foreign_key)
    foreign_device = store.register_device("u2", "android", foreign_public_b64, foreign_fingerprint, "unused-foreign")

    foreign_attempt = client.post(
        f"/v1/devices/{foreign_device}/revoke",
        headers={"Authorization": f"Bearer {owner_access}"},
    )
    assert foreign_attempt.status_code == 403
    assert foreign_attempt.json()["code"] == "DEVICE_SCOPE_MISMATCH"

    revoked = client.post(
        f"/v1/devices/{owner_device}/revoke",
        headers={"Authorization": f"Bearer {owner_access}"},
    )
    assert revoked.status_code == 200
    assert revoked.json() == {"revoked": True}
    assert store.get_session(owner_access) is None
    assert store.get_session(second_access) is None

    old_session = client.post(
        "/v1/authorize",
        headers={"Authorization": f"Bearer {second_access}"},
        json={"action": "character:read", "resource": "character:42"},
    )
    assert old_session.status_code == 401
