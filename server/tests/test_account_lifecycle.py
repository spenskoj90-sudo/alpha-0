from __future__ import annotations

import os
import uuid

from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from app.main import app


def test_account_export_requires_auth_and_erasure_requires_reauth() -> None:
    client = TestClient(app)
    suffix = uuid.uuid4().hex
    email = f"erase-{suffix}@example.com"
    password = f"Correct-Horse-Battery-Staple-{suffix}"
    registration = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 200
    token = registration.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/v1/account/export").status_code == 401
    exported = client.get("/v1/account/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["profile"]["email"] == email
    assert "password_hash" not in str(exported.json())

    denied = client.post("/v1/account/erase", headers=headers, json={"password": password + "wrong", "confirmation": "ERASE"})
    assert denied.status_code == 403
    erased = client.post("/v1/account/erase", headers=headers, json={"password": password, "confirmation": "ERASE"})
    assert erased.status_code == 200
    assert erased.json()["status"] == "ERASED"

    # The bearer used to authorize erasure was revoked as part of the same operation.
    assert client.get("/v1/account/export", headers=headers).status_code == 401
    login = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 401
