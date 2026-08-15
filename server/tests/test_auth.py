from fastapi.testclient import TestClient

from app.main import app, store


client = TestClient(app)


def test_register_creates_hashed_user_session():
    email = "auth-register@example.com"
    password = "Correct-Horse-Battery-Staple-123"
    response = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["session_token"]
    assert body["refresh_token"]
    record = store.get_session(body["session_token"])
    assert record is not None
    assert record["user_id"] == email
    assert record["device_id"] is None


def test_login_issues_user_session_and_wrong_password_denies():
    email = "auth-login@example.com"
    password = "Correct-Horse-Battery-Staple-456"
    assert client.post("/v1/auth/register", json={"email": email, "password": password}).status_code == 200

    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    record = store.get_session(response.json()["session_token"])
    assert record is not None
    assert record["device_id"] is None

    denied = client.post("/v1/auth/login", json={"email": email, "password": "Wrong-password-123"})
    assert denied.status_code == 401
    assert denied.json()["code"] == "INVALID_CREDENTIALS"


def test_duplicate_registration_denies():
    email = "auth-duplicate@example.com"
    password = "Correct-Horse-Battery-Staple-789"
    assert client.post("/v1/auth/register", json={"email": email, "password": password}).status_code == 200
    duplicate = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_short_password_is_rejected():
    response = client.post("/v1/auth/register", json={"email": "auth-short@example.com", "password": "short"})
    assert response.status_code == 422


def test_user_session_can_refresh_and_revoke():
    response = client.post(
        "/v1/auth/register",
        json={"email": "auth-session@example.com", "password": "Correct-Horse-Battery-Staple-999"},
    )
    assert response.status_code == 200
    body = response.json()
    refreshed = client.post("/v1/sessions/refresh", json={"refresh_token": body["refresh_token"]})
    assert refreshed.status_code == 200
    new_token = refreshed.json()["session_token"]
    revoked = client.post("/v1/sessions/revoke", headers={"Authorization": f"Bearer {new_token}"})
    assert revoked.status_code == 200
    assert client.post("/v1/sessions/revoke", headers={"Authorization": f"Bearer {new_token}"}).status_code == 401
