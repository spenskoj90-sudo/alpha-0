import hashlib
import os
import time
import uuid

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from app import main as main_module
from app.core.federated_auth import VerifiedFederatedIdentity
from app.core.security import session_hash
from app.core.totp import decode_totp_secret, totp_at
from app.main import (
    REFRESH_TTL_SECONDS,
    SESSION_TTL_SECONDS,
    account_mfa,
    app,
    store,
    user_store,
)


client = TestClient(app)


def _current_code(secret: str) -> str:
    return totp_at(decode_totp_secret(secret), int(time.time() // 30))


def _bound_session(user_id: str) -> str:
    access, _, _, _ = store.issue_session(
        f"mfa-device-{uuid.uuid4()}",
        user_id,
        SESSION_TTL_SECONDS,
        REFRESH_TTL_SECONDS,
    )
    user_store.restrict_session_scopes(
        store,
        access,
        {"character:read", "game:read", "audit:read"},
    )
    return access


def _register(email: str, password: str) -> None:
    response = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _enable_mfa(monkeypatch, email: str, password: str) -> tuple[str, list[str]]:
    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    _register(email, password)
    access = _bound_session(email)
    enrolled = client.post(
        "/v1/account/mfa/totp/enroll",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert enrolled.status_code == 200, enrolled.text
    secret = enrolled.json()["secret"]
    assert secret not in account_mfa._memory[email]["secret_ciphertext"]
    confirmed = client.post(
        "/v1/account/mfa/totp/confirm",
        headers={"Authorization": f"Bearer {access}"},
        json={"code": _current_code(secret)},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "MFA_ENABLED"
    recovery = confirmed.json()["recovery_codes"]
    assert len(recovery) == 10
    assert store.get_session(access) is None
    return secret, recovery


def test_mfa_login_challenge_blocks_session_until_second_factor(monkeypatch):
    email = f"mfa-login-{uuid.uuid4().hex}@example.com"
    password = "Correct-Horse-Battery-Staple-MFA-1"
    secret, recovery = _enable_mfa(monkeypatch, email, password)

    first_factor = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert first_factor.status_code == 200
    payload = first_factor.json()
    assert payload["mfa_required"] is True
    assert "session_token" not in payload
    challenge = payload["challenge_token"]
    assert challenge not in account_mfa._challenges
    assert hashlib.sha256(challenge.encode()).hexdigest() in account_mfa._challenges

    denied = client.post(
        "/v1/auth/mfa/complete",
        json={"challenge_token": challenge, "code": "000000"},
    )
    assert denied.status_code == 401

    # Enrollment consumes the current TOTP counter, so the same 30-second
    # code must not be accepted again for the immediately following login.
    completed = client.post(
        "/v1/auth/mfa/complete",
        json={"challenge_token": challenge, "code": recovery[0]},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["session_token"]
    replay = client.post(
        "/v1/auth/mfa/complete",
        json={"challenge_token": challenge, "code": recovery[1]},
    )
    assert replay.status_code == 401


def test_recovery_code_is_one_time_login_factor(monkeypatch):
    email = f"mfa-recovery-{uuid.uuid4().hex}@example.com"
    password = "Correct-Horse-Battery-Staple-MFA-2"
    _, recovery = _enable_mfa(monkeypatch, email, password)

    first = client.post("/v1/auth/login", json={"email": email, "password": password}).json()
    completed = client.post(
        "/v1/auth/mfa/complete",
        json={"challenge_token": first["challenge_token"], "code": recovery[0]},
    )
    assert completed.status_code == 200

    second = client.post("/v1/auth/login", json={"email": email, "password": password}).json()
    replay = client.post(
        "/v1/auth/mfa/complete",
        json={"challenge_token": second["challenge_token"], "code": recovery[0]},
    )
    assert replay.status_code == 401


def test_mfa_security_state_and_disable_revoke_sessions(monkeypatch):
    email = f"mfa-disable-{uuid.uuid4().hex}@example.com"
    password = "Correct-Horse-Battery-Staple-MFA-3"
    _, recovery = _enable_mfa(monkeypatch, email, password)

    first = client.post("/v1/auth/login", json={"email": email, "password": password}).json()
    session = client.post(
        "/v1/auth/mfa/complete",
        json={"challenge_token": first["challenge_token"], "code": recovery[0]},
    ).json()["session_token"]
    device_bound = _bound_session(email)

    state = client.get(
        "/v1/account/security",
        headers={"Authorization": f"Bearer {device_bound}"},
    )
    assert state.status_code == 200
    assert state.json()["mfa_enabled"] is True
    assert state.json()["mfa_recovery_codes_remaining"] == 9

    disabled = client.post(
        "/v1/account/mfa/totp/disable",
        headers={"Authorization": f"Bearer {device_bound}"},
        json={"code": recovery[1]},
    )
    assert disabled.status_code == 200
    assert disabled.json() == {"status": "MFA_DISABLED"}
    assert store.get_session(session) is None
    assert store.get_session(device_bound) is None

    password_only = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert password_only.status_code == 200
    assert password_only.json()["session_token"]


def test_federated_first_factor_cannot_bypass_enabled_mfa(monkeypatch):
    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("SENTINEL_GOOGLE_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_GOOGLE_WEB_CLIENT_ID", "mfa-test.apps.googleusercontent.com")
    subject = f"google-mfa-{uuid.uuid4().hex}"
    email = f"google-mfa-{uuid.uuid4().hex}@gmail.com"
    monkeypatch.setattr(
        main_module,
        "verify_google_id_token",
        lambda _token, _nonce: VerifiedFederatedIdentity(
            provider="google",
            subject=subject,
            email=email,
            email_verified=True,
        ),
    )

    first_nonce = client.post("/v1/auth/providers/google/challenge").json()["nonce"]
    first_login = client.post(
        "/v1/auth/providers/google/login",
        json={"id_token": "g" * 64, "nonce": first_nonce},
    )
    assert first_login.status_code == 200
    assert first_login.json()["session_token"]
    user_id = user_store.external_identity_user("google", subject)
    assert user_id is not None

    bound = _bound_session(user_id)
    enrolled = client.post(
        "/v1/account/mfa/totp/enroll",
        headers={"Authorization": f"Bearer {bound}"},
    )
    assert enrolled.status_code == 200
    secret = enrolled.json()["secret"]
    enabled = client.post(
        "/v1/account/mfa/totp/confirm",
        headers={"Authorization": f"Bearer {bound}"},
        json={"code": _current_code(secret)},
    )
    assert enabled.status_code == 200
    recovery = enabled.json()["recovery_codes"]

    second_nonce = client.post("/v1/auth/providers/google/challenge").json()["nonce"]
    second_login = client.post(
        "/v1/auth/providers/google/login",
        json={"id_token": "h" * 64, "nonce": second_nonce},
    )
    assert second_login.status_code == 200
    payload = second_login.json()
    assert payload["mfa_required"] is True
    assert "session_token" not in payload

    completed = client.post(
        "/v1/auth/mfa/complete",
        json={"challenge_token": payload["challenge_token"], "code": recovery[0]},
    )
    assert completed.status_code == 200
    assert completed.json()["session_token"]


def test_mfa_enrollment_fails_closed_without_encryption_key(monkeypatch):
    monkeypatch.delenv("SENTINEL_ACCOUNT_MFA_KEY", raising=False)
    email = f"mfa-key-{uuid.uuid4().hex}@example.com"
    password = "Correct-Horse-Battery-Staple-MFA-4"
    _register(email, password)
    access = _bound_session(email)

    response = client.post(
        "/v1/account/mfa/totp/enroll",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "ACCOUNT_MFA_KEY_NOT_CONFIGURED"
