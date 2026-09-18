import hashlib
import re
import uuid

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.email_provider import TestEmailTransport
from app.main import app, store, user_store


client = TestClient(app)


def test_register_creates_hashed_user_session():
    email = "auth-register@example.com"
    password = "Correct-Horse-Battery-Staple-123"
    response = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["session_token"]
    assert body["refresh_token"]
    assert set(body["scopes"]) == {"character:read", "game:read", "audit:read"}
    record = store.get_session(body["session_token"])
    assert record is not None
    assert record["user_id"] == email
    assert record["device_id"] is None
    assert "game:write" not in record["scopes"]


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


def test_user_session_can_refresh_and_revoke_without_scope_escalation():
    response = client.post(
        "/v1/auth/register",
        json={"email": "auth-session@example.com", "password": "Correct-Horse-Battery-Staple-999"},
    )
    assert response.status_code == 200
    body = response.json()
    refreshed = client.post("/v1/sessions/refresh", json={"refresh_token": body["refresh_token"]})
    assert refreshed.status_code == 200
    assert set(refreshed.json()["scopes"]) == {"character:read", "game:read", "audit:read"}
    new_token = refreshed.json()["session_token"]
    record = store.get_session(new_token)
    assert record is not None
    assert record["device_id"] is None
    assert "game:write" not in record["scopes"]
    revoked = client.post("/v1/sessions/revoke", headers={"Authorization": f"Bearer {new_token}"})
    assert revoked.status_code == 200
    assert client.post("/v1/sessions/revoke", headers={"Authorization": f"Bearer {new_token}"}).status_code == 401


def _message_token(text: str, label: str) -> str:
    match = re.search(rf"{label}: ([A-Za-z0-9_-]+)", text)
    assert match is not None
    return match.group(1)


def test_email_verification_is_hashed_single_use_and_updates_security_state(monkeypatch):
    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, "email_transport", transport)
    email = f"verify-{uuid.uuid4().hex}@example.com"
    password = "Account-verification-test-password-123"

    registered = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 200
    token = _message_token(transport.snapshot()[0].text, "Verification code")
    assert token not in user_store._action_tokens
    assert hashlib.sha256(token.encode()).hexdigest() in user_store._action_tokens

    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    before = client.get("/v1/account/security", headers=headers)
    assert before.status_code == 200
    assert before.json()["email_verified"] is False
    assert before.json()["providers"] == []

    confirmed = client.post("/v1/auth/email-verification/confirm", json={"token": token})
    assert confirmed.status_code == 200
    assert confirmed.json() == {"status": "VERIFIED"}
    assert client.post("/v1/auth/email-verification/confirm", json={"token": token}).status_code == 400
    assert client.get("/v1/account/security", headers=headers).json()["email_verified"] is True


def test_account_action_requests_do_not_enumerate_unknown_email(monkeypatch):
    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, "email_transport", transport)
    missing = f"missing-{uuid.uuid4().hex}@example.com"

    verification = client.post("/v1/auth/email-verification/request", json={"email": missing})
    reset = client.post("/v1/auth/password-reset/request", json={"email": missing})

    assert verification.status_code == 202
    assert reset.status_code == 202
    assert verification.json() == {"status": "ACCEPTED"}
    assert reset.json() == {"status": "ACCEPTED"}
    assert transport.snapshot() == ()


def test_password_reset_changes_password_revokes_sessions_and_rejects_replay(monkeypatch):
    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, "email_transport", transport)
    email = f"reset-{uuid.uuid4().hex}@example.com"
    old_password = "Account-reset-old-password-12345"
    new_password = "Account-reset-new-password-98765"

    registered = client.post("/v1/auth/register", json={"email": email, "password": old_password})
    assert registered.status_code == 200
    old_access = registered.json()["session_token"]
    prior_messages = len(transport.snapshot())

    requested = client.post("/v1/auth/password-reset/request", json={"email": email})
    assert requested.status_code == 202
    messages = transport.snapshot()
    assert len(messages) == prior_messages + 1
    token = _message_token(messages[-1].text, "Reset code")
    assert token not in user_store._action_tokens
    assert hashlib.sha256(token.encode()).hexdigest() in user_store._action_tokens

    confirmed = client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "password": new_password},
    )
    assert confirmed.status_code == 200
    assert confirmed.json() == {"status": "PASSWORD_UPDATED"}
    assert store.get_session(old_access) is None

    replay = client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "password": "Account-reset-third-password-45678"},
    )
    assert replay.status_code == 400
    assert client.post("/v1/auth/login", json={"email": email, "password": old_password}).status_code == 401
    assert client.post("/v1/auth/login", json={"email": email, "password": new_password}).status_code == 200
