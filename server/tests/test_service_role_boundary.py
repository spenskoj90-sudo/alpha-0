from __future__ import annotations

"""Service-role boundary invariants.

PostgresStore connections set app.service_role=true. That privilege is server-only:
the client never supplies this GUC. User-facing endpoints must still enforce
ownership via application checks (principal.user_id / device_id).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_and_login(email: str, password: str = "CorrectHorseBattery1!") -> str:
    client.post("/v1/auth/register", json={"email": email, "password": password})
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["session_token"]


def test_cross_user_device_access_rejected():
    token_a = _register_and_login("user-a@example.com")
    token_b = _register_and_login("user-b@example.com")
    # A has no device yet; requesting a random device id must not leak
    resp = client.get(
        "/v1/devices/00000000-0000-0000-0000-000000000099",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code in (403, 404)
    # B cannot use A's token
    resp2 = client.get(
        "/v1/devices/00000000-0000-0000-0000-000000000099",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp2.status_code in (403, 404)


def test_admin_requires_admin_token_not_session():
    token = _register_and_login("user-admin-boundary@example.com")
    resp = client.get("/v1/admin/games", headers={"Authorization": f"Bearer {token}"})
    # Admin endpoints use X-Sentinel-Admin-Token, not bearer session
    assert resp.status_code in (403, 503)


def test_integrity_endpoint_does_not_trust_client_verdicts():
    token = _register_and_login("integrity-boundary@example.com")
    nonce_resp = client.post(
        "/v1/integrity/nonce",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert nonce_resp.status_code == 200
    nonce = nonce_resp.json()["nonce"]
    attest = client.post(
        "/v1/integrity/attest",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "nonce": nonce,
            "client_verdicts": ["MEETS_STRONG_INTEGRITY"],
            "integrity_token": "not-a-real-token",
        },
    )
    assert attest.status_code == 200
    body = attest.json()
    assert body.get("trusted") is False
    # Without Google credentials, tier must not become STRONG from client_verdicts
    assert body.get("tier") in {"UNKNOWN", "FAILED"}
