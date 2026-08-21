import base64
import hashlib
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

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


def bind_user():
    reset_store()
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    public_b64 = base64.b64encode(public).decode()
    fingerprint = hashlib.sha256(public).hexdigest()
    registered = client.post(
        "/v1/devices/register",
        headers={"X-Enrollment-Token": "u1:secret"},
        json={"user_id": "u1", "platform": "android", "public_key_der_b64": public_b64, "fingerprint_sha256": fingerprint},
    )
    assert registered.status_code == 200
    session = client.post("/v1/auth/login", json={"email": "u1@example.com", "password": "not-a-real-password"})
    assert session.status_code in {401, 404}
    return registered.json(), public_b64, fingerprint


def test_device_detail_is_scoped_to_authenticated_user():
    reset_store()
    device_id = store.register_device("u1", "android", "A" * 32, "1" * 64, "challenge")
    token, _, _, _ = store.issue_session(None, "u1", 3600, 3600)
    response = client.get(f"/v1/devices/{device_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["device_id"] == device_id
    assert response.json()["state"] == "ACTIVE"


def test_entitlements_are_user_scoped_and_enriched_with_game_data():
    reset_store()
    item = {
        "id": "ent-1",
        "user_id": "u1",
        "game_id": "diablo-immortal-android",
        "source": "test",
        "status": "ACTIVE",
        "valid_from": "2026-08-01T00:00:00+00:00",
        "valid_until": "2026-12-31T00:00:00+00:00",
    }
    store.create_entitlement(item)
    token, _, _, _ = store.issue_session(None, "u1", 3600, 3600)
    headers = {"Authorization": f"Bearer {token}"}
    listed = client.get("/v1/entitlements/me", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["entitlements"][0]["game_name"] == "Diablo Immortal"
    detail = client.get("/v1/entitlements/ent-1", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["platform"] == "android"
    assert detail.json()["status"] == "ACTIVE"


def test_entitlement_cannot_be_read_by_another_user():
    reset_store()
    store.create_entitlement({
        "id": "ent-2",
        "user_id": "u1",
        "game_id": "diablo-4-pc",
        "source": "test",
        "status": "ACTIVE",
        "valid_from": "2026-08-01T00:00:00+00:00",
        "valid_until": "2026-12-31T00:00:00+00:00",
    })
    token, _, _, _ = store.issue_session(None, "u2", 3600, 3600)
    response = client.get("/v1/entitlements/ent-2", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
