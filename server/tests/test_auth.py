import hashlib
import re
import uuid

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.email_provider import DisabledEmailTransport, TestEmailTransport
from app.main import app, store, user_store


client = TestClient(app)


def test_unknown_web_revoke_and_invalid_refresh_do_not_allocate_families():
    family = "unknown-web-" + uuid.uuid4().hex + "x" * 24
    before = dict(store.web_session_families)
    assert client.post("/v1/sessions/web/revoke", headers={"X-Sentinel-Web-Session": family}).status_code == 409
    assert client.post("/v1/sessions/refresh", headers={"X-Sentinel-Web-Session": family},
                       json={"refresh_token": "invalid-refresh-" + "x" * 48}).status_code == 401
    assert store.web_session_families == before


def test_invalid_login_does_not_allocate_a_web_family():
    family = "invalid-login-" + uuid.uuid4().hex + "x" * 24
    before = dict(store.web_session_families)
    denied = client.post("/v1/auth/login", headers={"X-Sentinel-Web-Session": family},
                         json={"email": f"{uuid.uuid4().hex}@example.com", "password": "wrong-password-123"})
    assert denied.status_code == 401
    assert store.web_session_families == before


def test_invalid_refresh_does_not_reserve_or_cancel_known_family_operations():
    from app.core.security import session_hash
    family = "known-invalid-refresh-" + uuid.uuid4().hex + "x" * 24
    store.begin_web_session_operation(family)
    before = {**store.web_session_families[session_hash(family)]}
    before["cancelled_operations"] = set(before["cancelled_operations"])
    denied = client.post("/v1/sessions/refresh", headers={"X-Sentinel-Web-Session": family},
                         json={"refresh_token": "invalid-refresh-" + "x" * 48})
    assert denied.status_code == 401
    assert store.web_session_families[session_hash(family)] == before


def test_logout_supersedes_known_family_login_during_password_verification(monkeypatch):
    family = "known-login-logout-" + uuid.uuid4().hex + "x" * 24
    email = f"{uuid.uuid4().hex}@example.com"
    password = "Login-logout-race-password-123"
    headers = {"X-Sentinel-Web-Session": family}
    created = client.post("/v1/auth/register", headers=headers, json={"email": email, "password": password})
    assert created.status_code == 200
    original = user_store.authenticate

    def authenticate_after_logout(*args):
        assert client.post("/v1/sessions/web/revoke", headers=headers).status_code == 200
        return original(*args)

    monkeypatch.setattr(user_store, "authenticate", authenticate_after_logout)
    accepted = client.post("/v1/auth/login", headers=headers, json={"email": email, "password": password})
    assert accepted.status_code == 409
    assert accepted.json()["code"] == "WEB_SESSION_SUPERSEDED"
    assert store.get_session(created.json()["session_token"]) is None


def test_registration_claim_cleanup_failure_does_not_replace_committed_result(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    class Engine:
        calls = 0

        @contextmanager
        def begin(self):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("cleanup unavailable")
            yield self

        def execute(self, statement, values):
            return SimpleNamespace(scalar_one_or_none=lambda: values.get("claim"))

    monkeypatch.setattr(main_module, "store", SimpleNamespace(engine=Engine()))
    with main_module.claimed_web_registration("claim-cleanup-" + "x" * 48) as acquired:
        assert acquired is True
        result = "committed"
    assert result == "committed"


def test_registration_claim_acquisition_failure_still_fails_closed(monkeypatch):
    from types import SimpleNamespace
    import pytest

    def unavailable():
        raise RuntimeError("claim acquisition unavailable")

    monkeypatch.setattr(main_module, "store", SimpleNamespace(engine=SimpleNamespace(begin=unavailable)))
    with pytest.raises(RuntimeError, match="claim acquisition unavailable"):
        with main_module.claimed_web_registration("claim-acquisition-" + "x" * 48):
            raise AssertionError("must not perform registration")


def test_full_reservation_window_returns_bounded_error_and_logout_remains_available():
    family = "full-window-api-" + uuid.uuid4().hex + "x" * 24
    for _ in range(256):
        operation = store.begin_web_session_operation(family)
        store.cancel_web_session_operation(family, operation)
    headers = {"X-Sentinel-Web-Session": family}
    denied = client.post("/v1/auth/login", headers=headers,
                         json={"email": "unused@example.com", "password": "wrong-password-123"})
    assert denied.status_code == 429
    assert denied.json()["code"] == "WEB_SESSION_OPERATION_LIMIT"
    assert client.post("/v1/sessions/web/revoke", headers=headers).status_code == 200


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


def test_web_session_family_makes_prior_login_and_refresh_generations_stale():
    email = f"web-generation-{uuid.uuid4().hex}@example.com"
    password = "Web-session-generation-password-123"
    family = "web-family-" + "c" * 48
    headers = {"X-Sentinel-Web-Session": family}
    assert client.post("/v1/auth/register", json={"email": email, "password": password}).status_code == 200

    first = client.post("/v1/auth/login", headers=headers, json={"email": email, "password": password})
    second = client.post("/v1/auth/login", headers=headers, json={"email": email, "password": password})
    assert first.status_code == second.status_code == 200
    assert first.headers["x-sentinel-web-generation"] == "1"
    assert second.headers["x-sentinel-web-generation"] == "2"
    assert store.get_session(first.json()["session_token"]) is None
    assert store.get_session(second.json()["session_token"]) is not None

    refreshed = client.post(
        "/v1/sessions/refresh",
        headers=headers,
        json={"refresh_token": second.json()["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.headers["x-sentinel-web-generation"] == "3"
    assert store.get_session(second.json()["session_token"]) is None

    logged_out = client.post("/v1/sessions/web/revoke", headers=headers)
    assert logged_out.status_code == 200
    assert logged_out.headers["x-sentinel-web-generation"] == "4"
    assert store.get_session(refreshed.json()["session_token"]) is None


def test_web_logout_revokes_presented_legacy_refresh_without_access_cookie():
    family = "web-legacy-logout-" + "l" * 48
    legacy_access, legacy_refresh, _, _ = store.issue_session(
        None, f"legacy-{uuid.uuid4().hex}@example.com", 3600, 7200
    )

    logged_out = client.post(
        "/v1/sessions/web/revoke",
        headers={"X-Sentinel-Web-Session": family},
        json={"refresh_token": legacy_refresh},
    )

    assert logged_out.status_code == 200
    assert store.get_session(legacy_access) is None
    assert client.post(
        "/v1/sessions/refresh", json={"refresh_token": legacy_refresh}
    ).status_code == 401


def test_failed_duplicate_registration_does_not_supersede_account_creator(monkeypatch):
    email = f"register-race-{uuid.uuid4().hex}@example.com"
    password = "Registration-race-password-123"
    family = "web-registration-race-" + "r" * 48
    original_register = user_store.register
    nested = False

    def register_with_duplicate(candidate_email, candidate_password):
        nonlocal nested
        if not nested:
            nested = True
            duplicate = client.post(
                "/v1/auth/register",
                headers={"X-Sentinel-Web-Session": family},
                json={"email": email, "password": password},
            )
            assert duplicate.status_code == 409
            assert duplicate.json()["code"] == "REGISTRATION_IN_PROGRESS"
        return original_register(candidate_email, candidate_password)

    monkeypatch.setattr(user_store, "register", register_with_duplicate)
    created = client.post(
        "/v1/auth/register",
        headers={"X-Sentinel-Web-Session": family},
        json={"email": email, "password": password},
    )

    assert created.status_code == 200
    assert created.headers["x-sentinel-web-generation"] == "1"


def test_failed_later_login_cancels_reservation_before_earlier_login_commits(monkeypatch):
    email = f"login-race-{uuid.uuid4().hex}@example.com"
    password = "Login-race-password-123"
    family = "web-login-race-" + "q" * 48
    headers = {"X-Sentinel-Web-Session": family}
    assert client.post("/v1/auth/register", json={"email": email, "password": password}).status_code == 200
    original_authenticate = user_store.authenticate
    nested = False

    def authenticate_with_rejected_later(candidate_email, candidate_password):
        nonlocal nested
        if candidate_password == password and not nested:
            nested = True
            denied = client.post(
                "/v1/auth/login",
                headers=headers,
                json={"email": email, "password": "Definitely-wrong-password-456"},
            )
            assert denied.status_code == 401
        return original_authenticate(candidate_email, candidate_password)

    monkeypatch.setattr(user_store, "authenticate", authenticate_with_rejected_later)
    accepted = client.post(
        "/v1/auth/login",
        headers=headers,
        json={"email": email, "password": password},
    )

    assert accepted.status_code == 200
    assert accepted.headers["x-sentinel-web-generation"] == "1"


def test_failed_later_refresh_cancels_reservation_before_earlier_login_commits(monkeypatch):
    email = f"refresh-race-{uuid.uuid4().hex}@example.com"
    password = "Refresh-race-password-123"
    family = "web-refresh-race-" + "v" * 48
    headers = {"X-Sentinel-Web-Session": family}
    assert client.post("/v1/auth/register", json={"email": email, "password": password}).status_code == 200
    original_authenticate = user_store.authenticate
    nested = False

    def authenticate_with_rejected_refresh(candidate_email, candidate_password):
        nonlocal nested
        if not nested:
            nested = True
            denied = client.post(
                "/v1/sessions/refresh",
                headers=headers,
                json={"refresh_token": "invalid-one-use-refresh-" + "x" * 48},
            )
            assert denied.status_code == 401
        return original_authenticate(candidate_email, candidate_password)

    monkeypatch.setattr(user_store, "authenticate", authenticate_with_rejected_refresh)
    accepted = client.post(
        "/v1/auth/login",
        headers=headers,
        json={"email": email, "password": password},
    )

    assert accepted.status_code == 200
    assert accepted.headers["x-sentinel-web-generation"] == "1"


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
    assert re.fullmatch(r"[0-9]{8}", token)
    assert hashlib.sha256(token.encode()).hexdigest() not in user_store._action_tokens
    action = next(a for a in user_store._action_tokens.values() if a["user_id"] == email and a["consumed_at"] is None and a["purpose"] == "EMAIL_VERIFY")
    assert action["code_hash"].startswith("scrypt$")
    from app.core.auth import verify_password
    assert verify_password(token, action["code_hash"])

    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    before = client.get("/v1/account/security", headers=headers)
    assert before.status_code == 200
    assert before.json()["email_verified"] is False
    assert before.json()["providers"] == []

    confirmed = client.post("/v1/auth/email-verification/confirm", json={"token": token, "email": email})
    assert confirmed.status_code == 200
    assert confirmed.json() == {"status": "VERIFIED"}
    assert client.post("/v1/auth/email-verification/confirm", json={"token": token, "email": email}).status_code == 400
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


def test_authenticated_email_verification_reports_delivery_provider_state(monkeypatch):
    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, "email_transport", transport)
    email = f"verify-account-{uuid.uuid4().hex}@example.com"
    password = "Account-verification-provider-state-123"

    registered = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 200
    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}

    delivered = client.post("/v1/account/email-verification/request", headers=headers)
    assert delivered.status_code == 202
    assert delivered.json() == {"status": "ACCEPTED"}
    assert len(transport.snapshot()) == 2

    monkeypatch.setattr(main_module, "email_transport", DisabledEmailTransport())
    unavailable = client.post("/v1/account/email-verification/request", headers=headers)
    assert unavailable.status_code == 503
    assert unavailable.json()["code"] == "EMAIL_PROVIDER_UNAVAILABLE"

    public_request = client.post("/v1/auth/email-verification/request", json={"email": email})
    assert public_request.status_code == 202
    assert public_request.json() == {"status": "ACCEPTED"}


def test_authenticated_email_verification_requires_valid_session(monkeypatch):
    monkeypatch.setattr(main_module, "email_transport", TestEmailTransport())
    response = client.post(
        "/v1/account/email-verification/request",
        headers={"Authorization": "Bearer not-a-valid-session"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_SESSION"


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
    assert re.fullmatch(r"[0-9]{8}", token)
    assert hashlib.sha256(token.encode()).hexdigest() not in user_store._action_tokens
    action = next(a for a in user_store._action_tokens.values() if a["user_id"] == email and a["consumed_at"] is None and a["purpose"] == "PASSWORD_RESET")
    assert action["code_hash"].startswith("scrypt$")
    from app.core.auth import verify_password
    assert verify_password(token, action["code_hash"])

    confirmed = client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "email": email, "password": new_password},
    )
    assert confirmed.status_code == 200
    assert confirmed.json() == {"status": "PASSWORD_UPDATED"}
    assert store.get_session(old_access) is None

    replay = client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "email": email, "password": "Account-reset-third-password-45678"},
    )
    assert replay.status_code == 400
    assert client.post("/v1/auth/login", json={"email": email, "password": old_password}).status_code == 401
    assert client.post("/v1/auth/login", json={"email": email, "password": new_password}).status_code == 200


def test_password_reset_commits_family_tombstone_after_password_mutation(monkeypatch):
    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, "email_transport", transport)
    email = f"reset-family-race-{uuid.uuid4().hex}@example.com"
    old_password = "Reset-family-old-password-123"
    new_password = "Reset-family-new-password-456"
    family = "web-reset-family-" + "p" * 48
    assert client.post("/v1/auth/register", json={"email": email, "password": old_password}).status_code == 200
    assert client.post("/v1/auth/password-reset/request", json={"email": email}).status_code == 202
    token = _message_token(transport.snapshot()[-1].text, "Reset code")
    original_reset = user_store.reset_password

    def reset_with_interleaved_operation(*args, **kwargs):
        result = original_reset(*args, **kwargs)
        store.begin_web_session_operation(family)
        return result

    monkeypatch.setattr(user_store, "reset_password", reset_with_interleaved_operation)
    confirmed = client.post(
        "/v1/auth/password-reset/confirm",
        headers={"X-Sentinel-Web-Session": family},
        json={"token": token, "email": email, "password": new_password},
    )

    assert confirmed.status_code == 200
    assert confirmed.json() == {"status": "PASSWORD_UPDATED"}
    assert int(confirmed.headers["x-sentinel-web-generation"]) >= 2
