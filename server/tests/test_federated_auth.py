from __future__ import annotations

import base64
import json
import time
import uuid

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient

from app import main as main_module
from app.core import federated_auth as federated_module
from app.core.federated_auth import (
    FederatedAuthError,
    VerifiedFederatedIdentity,
    complete_telegram,
    complete_vk,
    provider_statuses,
    verify_google_id_token,
)
from app.core.user_store import UserAccountStore
from app.main import app, user_store


client = TestClient(app)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _rsa_jwk_and_token(claims: dict, *, kid: str = "test-key") -> tuple[dict, str]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "n": _b64url(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
    }
    header = _b64url(json.dumps({"alg": "RS256", "kid": kid}, separators=(",", ":")).encode())
    payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signed = f"{header}.{payload}".encode()
    signature = private.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    return {"keys": [jwk]}, f"{header}.{payload}.{_b64url(signature)}"


def _google_env(monkeypatch) -> str:
    client_id = "sentinel-test.apps.googleusercontent.com"
    monkeypatch.setenv("SENTINEL_GOOGLE_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_GOOGLE_WEB_CLIENT_ID", client_id)
    return client_id


def test_google_id_token_verifies_signature_audience_issuer_nonce_and_authoritative_email(monkeypatch):
    client_id = _google_env(monkeypatch)
    now = int(time.time())
    nonce = "nonce-value-for-test"
    jwks, token = _rsa_jwk_and_token(
        {
            "iss": "https://accounts.google.com",
            "sub": "google-subject-1",
            "aud": client_id,
            "iat": now - 5,
            "exp": now + 300,
            "nonce": nonce,
            "email": "Owner@gmail.com",
            "email_verified": True,
        }
    )
    identity = verify_google_id_token(token, nonce, now=now, jwks_fetcher=lambda: jwks)
    assert identity.provider == "google"
    assert identity.subject == "google-subject-1"
    assert identity.email == "owner@gmail.com"
    assert identity.email_verified is True

    with pytest.raises(FederatedAuthError, match="FEDERATED_NONCE_INVALID"):
        verify_google_id_token(token, "wrong-nonce", now=now, jwks_fetcher=lambda: jwks)


def test_google_third_party_email_is_not_promoted_to_sentinel_verified(monkeypatch):
    client_id = _google_env(monkeypatch)
    now = int(time.time())
    jwks, token = _rsa_jwk_and_token(
        {
            "iss": "accounts.google.com",
            "sub": "google-subject-third-party",
            "aud": client_id,
            "iat": now,
            "exp": now + 300,
            "nonce": "nonce",
            "email": "person@example.net",
            "email_verified": True,
        }
    )
    identity = verify_google_id_token(token, "nonce", now=now, jwks_fetcher=lambda: jwks)
    assert identity.email == "person@example.net"
    assert identity.email_verified is False


def test_provider_only_account_and_explicit_link_boundary_are_fail_closed():
    accounts = UserAccountStore(None)
    local_email = f"local-{uuid.uuid4().hex}@example.com"
    accounts.register(local_email, "local-password-long-enough")

    with pytest.raises(ValueError, match="ACCOUNT_LINK_REQUIRED"):
        accounts.register_external_account(
            "google",
            "different-google-subject",
            email=local_email,
            email_verified=True,
        )

    provider_user = accounts.register_external_account(
        "telegram",
        f"telegram-{uuid.uuid4().hex}",
        email=None,
        email_verified=False,
    )
    state = accounts.security_state(provider_user)
    assert state is not None
    assert state["email"] is None
    assert state["password_enabled"] is False
    assert state["providers"] == ["telegram"]


def test_federated_challenge_is_hashed_and_single_use():
    accounts = UserAccountStore(None)
    raw = accounts.issue_federated_challenge("google", "OIDC_NONCE", 300)
    assert raw not in accounts._federated_challenges
    assert accounts.consume_federated_challenge("google", "OIDC_NONCE", raw) == (True, None)
    assert accounts.consume_federated_challenge("google", "OIDC_NONCE", raw) == (False, None)


def test_google_api_login_consumes_nonce_once_and_does_not_expose_secret_config(monkeypatch):
    _google_env(monkeypatch)
    email = f"google-{uuid.uuid4().hex}@gmail.com"
    monkeypatch.setattr(
        main_module,
        "verify_google_id_token",
        lambda _token, _nonce: VerifiedFederatedIdentity(
            provider="google",
            subject=f"subject-{uuid.uuid4().hex}",
            email=email,
            email_verified=True,
        ),
    )
    catalog = client.get("/v1/auth/providers")
    assert catalog.status_code == 200
    google = next(item for item in catalog.json()["providers"] if item["provider"] == "google")
    assert google["enabled"] is True
    assert "secret" not in json.dumps(catalog.json()).lower()

    challenge = client.post("/v1/auth/providers/google/challenge")
    assert challenge.status_code == 200
    nonce = challenge.json()["nonce"]
    payload = {"id_token": "x" * 64, "nonce": nonce}

    login = client.post("/v1/auth/providers/google/login", json=payload)
    assert login.status_code == 200
    assert login.json()["session_token"]
    replay = client.post("/v1/auth/providers/google/login", json=payload)
    assert replay.status_code == 400
    assert replay.json()["code"] == "FEDERATED_CHALLENGE_INVALID"


def test_google_login_never_auto_links_existing_email(monkeypatch):
    _google_env(monkeypatch)
    email = f"collision-{uuid.uuid4().hex}@gmail.com"
    registered = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "collision-password-long-enough"},
    )
    assert registered.status_code == 200
    monkeypatch.setattr(
        main_module,
        "verify_google_id_token",
        lambda _token, _nonce: VerifiedFederatedIdentity(
            provider="google",
            subject=f"new-google-{uuid.uuid4().hex}",
            email=email,
            email_verified=True,
        ),
    )
    challenge = client.post("/v1/auth/providers/google/challenge").json()
    login = client.post(
        "/v1/auth/providers/google/login",
        json={"id_token": "y" * 64, "nonce": challenge["nonce"]},
    )
    assert login.status_code == 409
    assert login.json()["code"] == "ACCOUNT_LINK_REQUIRED"


def test_telegram_pkce_start_and_completion_reject_state_replay(monkeypatch):
    monkeypatch.setenv("SENTINEL_TELEGRAM_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_ID", "123456")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_SECRET", "test-only-secret")
    monkeypatch.setenv("SENTINEL_TELEGRAM_REDIRECT_URIS", "com.alpha0.app.auth.dev://callback")
    monkeypatch.setattr(
        main_module,
        "complete_telegram",
        lambda **_kwargs: VerifiedFederatedIdentity(
            provider="telegram",
            subject=f"telegram-{uuid.uuid4().hex}",
        ),
    )
    start = client.post(
        "/v1/auth/providers/telegram/start",
        json={"redirect_uri": "com.alpha0.app.auth.dev://callback"},
    )
    assert start.status_code == 200
    body = start.json()
    assert body["authorization_url"].startswith("https://oauth.telegram.org/auth?")
    assert body["code_verifier"] not in body["authorization_url"]
    assert f"nonce={body['state']}" in body["authorization_url"]

    complete = client.post(
        "/v1/auth/providers/telegram/complete",
        json={
            "code": "telegram-code",
            "state": body["state"],
            "code_verifier": body["code_verifier"],
        },
    )
    assert complete.status_code == 200
    replay = client.post(
        "/v1/auth/providers/telegram/complete",
        json={
            "code": "telegram-code",
            "state": body["state"],
            "code_verifier": body["code_verifier"],
        },
    )
    assert replay.status_code == 400
    assert replay.json()["code"] == "FEDERATED_CHALLENGE_INVALID"


def test_vk_exchange_uses_provider_subject_not_email(monkeypatch):
    monkeypatch.setenv("SENTINEL_VK_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_VK_CLIENT_ID", "123456")
    monkeypatch.setenv("SENTINEL_VK_REDIRECT_URIS", "vk123456://vk.ru/blank.html")
    identity = complete_vk(
        code="code",
        state="state",
        code_verifier="v" * 64,
        device_id="device",
        redirect_uri="vk123456://vk.ru/blank.html",
        token_fetcher=lambda: {"access_token": "access", "state": "state"},
        user_fetcher=lambda _token: {
            "user": {"user_id": 777, "email": "vk-user@example.com"}
        },
    )
    assert identity.subject == "777"
    assert identity.email == "vk-user@example.com"
    assert identity.email_verified is False


def test_telegram_id_token_verification_uses_oidc_subject(monkeypatch):
    monkeypatch.setenv("SENTINEL_TELEGRAM_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_ID", "123456")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("SENTINEL_TELEGRAM_REDIRECT_URIS", "com.alpha0.app.auth.dev://callback")
    now = int(time.time())
    jwks, token = _rsa_jwk_and_token(
        {
            "iss": "https://oauth.telegram.org",
            "sub": "telegram-subject",
            "aud": "123456",
            "iat": now,
            "exp": now + 300,
            "nonce": "telegram-test-state",
        }
    )
    identity = complete_telegram(
        code="code",
        code_verifier="z" * 64,
        redirect_uri="com.alpha0.app.auth.dev://callback",
        nonce="telegram-test-state",
        now=now,
        token_fetcher=lambda: {"id_token": token},
        jwks_fetcher=lambda: jwks,
    )
    assert identity == VerifiedFederatedIdentity(provider="telegram", subject="telegram-subject")


def test_disabled_providers_fail_closed(monkeypatch):
    for key in [
        "SENTINEL_GOOGLE_AUTH_ENABLED",
        "SENTINEL_GOOGLE_WEB_CLIENT_ID",
        "SENTINEL_TELEGRAM_AUTH_ENABLED",
        "SENTINEL_TELEGRAM_CLIENT_ID",
        "SENTINEL_TELEGRAM_CLIENT_SECRET",
        "SENTINEL_TELEGRAM_REDIRECT_URIS",
        "SENTINEL_VK_AUTH_ENABLED",
        "SENTINEL_VK_CLIENT_ID",
        "SENTINEL_VK_REDIRECT_URIS",
    ]:
        monkeypatch.delenv(key, raising=False)
    assert all(item.enabled is False for item in provider_statuses())
    assert client.post("/v1/auth/providers/google/challenge").status_code == 503


def test_browser_provider_rejects_redirect_not_in_server_allowlist(monkeypatch):
    monkeypatch.setenv("SENTINEL_TELEGRAM_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_ID", "123456")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv(
        "SENTINEL_TELEGRAM_REDIRECT_URIS",
        "com.alpha0.app.auth.dev://callback",
    )
    response = client.post(
        "/v1/auth/providers/telegram/start",
        json={"redirect_uri": "com.alpha0.app.auth://callback"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "FEDERATED_REDIRECT_URI_INVALID"


def test_google_provider_link_requires_authenticated_account_and_fresh_nonce(monkeypatch):
    _google_env(monkeypatch)
    email = f"link-{uuid.uuid4().hex}@example.com"
    registered = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "link-password-long-enough-123"},
    )
    assert registered.status_code == 200
    access = registered.json()["session_token"]
    provider_subject = f"google-link-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        main_module,
        "verify_google_id_token",
        lambda _token, _nonce: VerifiedFederatedIdentity(
            provider="google",
            subject=provider_subject,
            email=f"provider-{uuid.uuid4().hex}@gmail.com",
            email_verified=True,
        ),
    )
    challenge = client.post("/v1/auth/providers/google/challenge").json()
    payload = {"id_token": "z" * 64, "nonce": challenge["nonce"]}

    anonymous = client.post("/v1/account/providers/google/link", json=payload)
    assert anonymous.status_code == 422

    linked = client.post(
        "/v1/account/providers/google/link",
        headers={"Authorization": f"Bearer {access}"},
        json=payload,
    )
    assert linked.status_code == 200
    assert linked.json() == {"status": "LINKED"}

    security = client.get(
        "/v1/account/security",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert security.status_code == 200
    assert "google" in security.json()["providers"]

    replay = client.post(
        "/v1/account/providers/google/link",
        headers={"Authorization": f"Bearer {access}"},
        json=payload,
    )
    assert replay.status_code == 400
    assert replay.json()["code"] == "FEDERATED_CHALLENGE_INVALID"


def test_vk_network_exchange_matches_current_vkid_android_contract(monkeypatch):
    monkeypatch.setenv("SENTINEL_VK_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_VK_CLIENT_ID", "123456")
    monkeypatch.setenv("SENTINEL_VK_REDIRECT_URIS", "vk123456://vk.ru/blank.html")
    calls = []

    def fake_https_json(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/oauth2/auth"):
            return {"access_token": "vk-access", "state": "state"}
        return {"user": {"user_id": 42, "email": "vk42@example.com"}}

    monkeypatch.setattr(federated_module, "_https_json", fake_https_json)
    identity = complete_vk(
        code="authorization-code",
        state="state",
        code_verifier="p" * 64,
        device_id="vk-device",
        redirect_uri="vk123456://vk.ru/blank.html",
    )

    assert identity.subject == "42"
    assert calls[0][0] == "https://id.vk.ru/oauth2/auth"
    assert calls[0][1]["allowed_hosts"] == {"id.vk.ru"}
    assert calls[0][1]["form"] == {
        "grant_type": "authorization_code",
        "code": "authorization-code",
        "code_verifier": "p" * 64,
        "client_id": "123456",
        "device_id": "vk-device",
        "redirect_uri": "vk123456://vk.ru/blank.html",
        "state": "state",
    }
    assert calls[1][0].startswith("https://id.vk.ru/oauth2/user_info?")
    assert calls[1][1]["form"]["device_id"] == "vk-device"


def test_vk_provider_requires_canonical_vk_mobile_redirect(monkeypatch):
    monkeypatch.setenv("SENTINEL_VK_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_VK_CLIENT_ID", "123456")
    monkeypatch.setenv(
        "SENTINEL_VK_REDIRECT_URIS",
        "com.alpha0.app.auth.dev://callback",
    )
    vk = next(item for item in provider_statuses() if item.provider == "vk")
    assert vk.enabled is False
