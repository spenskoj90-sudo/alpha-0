from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.security import session_hash
from app.core.user_store import UserAccountStore


def test_memory_account_registration_authentication_and_security_state_boundaries() -> None:
    accounts = UserAccountStore(None)
    user = accounts.register(" Owner@Example.COM ", "Correct-Horse-Battery-Staple-1")
    assert user == "owner@example.com"
    assert accounts.authenticate("OWNER@example.com", "Correct-Horse-Battery-Staple-1") == user
    assert accounts.authenticate("owner@example.com", "wrong") is None
    assert accounts.authenticate("missing@example.com", "wrong") is None

    with pytest.raises(ValueError, match="EMAIL_ALREADY_REGISTERED"):
        accounts.register("owner@example.com", "another-password-long-enough")

    state = accounts.security_state(user)
    assert state == {
        "email": "owner@example.com",
        "email_verified": False,
        "password_enabled": True,
        "providers": [],
    }
    assert accounts.security_state("missing") is None

    accounts._users[user]["status"] = "SUSPENDED"
    assert accounts.authenticate(user, "Correct-Horse-Battery-Staple-1") is None
    assert accounts.security_state(user) is None

    accounts._users[user]["status"] = "ACTIVE"
    accounts._users[user]["password_hash"] = None
    assert accounts.authenticate(user, "Correct-Horse-Battery-Staple-1") is None


@pytest.mark.parametrize("purpose", ["", "LOGIN", "email_verify"])
def test_action_token_rejects_unknown_purpose(purpose: str) -> None:
    accounts = UserAccountStore(None)
    with pytest.raises(ValueError, match="AUTH_ACTION_PURPOSE_INVALID"):
        accounts.issue_action_token("x@example.com", purpose, 60)


@pytest.mark.parametrize("ttl", [0, -1, 172801])
def test_action_token_rejects_invalid_ttl(ttl: int) -> None:
    accounts = UserAccountStore(None)
    with pytest.raises(ValueError, match="AUTH_ACTION_TTL_INVALID"):
        accounts.issue_action_token("x@example.com", "EMAIL_VERIFY", ttl)


def test_action_tokens_are_non_enumerating_single_active_and_one_time() -> None:
    accounts = UserAccountStore(None)
    assert accounts.issue_action_token("missing@example.com", "EMAIL_VERIFY", 60) is None

    user = accounts.register("verify@example.com", "Correct-Horse-Battery-Staple-2")
    first = accounts.issue_action_token(user, "EMAIL_VERIFY", 60)
    second = accounts.issue_action_token(user, "EMAIL_VERIFY", 60)
    assert first and second and first != second
    assert accounts.confirm_email(first) is False
    assert accounts.confirm_email(second) is True
    assert accounts.confirm_email(second) is False
    assert accounts.security_state(user)["email_verified"] is True

    accounts._users[user]["status"] = "SUSPENDED"
    assert accounts.issue_action_token(user, "EMAIL_VERIFY", 60) is None


def test_email_confirmation_rejects_wrong_purpose_expiry_and_orphan_identity() -> None:
    accounts = UserAccountStore(None)
    user = accounts.register("confirm-boundaries@example.com", "Correct-Horse-Battery-Staple-3")

    reset = accounts.issue_action_token(user, "PASSWORD_RESET", 60)
    assert reset and accounts.confirm_email(reset) is False

    verify = accounts.issue_action_token(user, "EMAIL_VERIFY", 60)
    assert verify
    verify_hash = accounts._action_hash(verify)
    accounts._action_tokens[verify_hash]["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    assert accounts.confirm_email(verify) is False

    orphan = accounts.issue_action_token(user, "EMAIL_VERIFY", 60)
    assert orphan
    accounts._users.pop(user)
    assert accounts.confirm_email(orphan) is False


def test_password_reset_is_one_time_and_revokes_all_account_sessions() -> None:
    accounts = UserAccountStore(None)
    user = accounts.register("reset@example.com", "Correct-Horse-Battery-Staple-4")
    store = SimpleNamespace(
        sessions={
            "one": {"user_id": user, "revoked": False},
            "two": {"user_id": user, "revoked": False},
            "foreign": {"user_id": "foreign", "revoked": False},
        }
    )

    verify = accounts.issue_action_token(user, "EMAIL_VERIFY", 60)
    assert verify and accounts.reset_password(verify, "New-Correct-Horse-Battery-Staple-4", store) is None

    reset = accounts.issue_action_token(user, "PASSWORD_RESET", 60)
    assert reset
    assert accounts.reset_password(reset, "New-Correct-Horse-Battery-Staple-4", store) == user
    assert accounts.reset_password(reset, "Another-Correct-Horse-Battery-Staple-4", store) is None
    assert store.sessions["one"]["revoked"] is True
    assert store.sessions["two"]["revoked"] is True
    assert store.sessions["foreign"]["revoked"] is False
    assert accounts.authenticate(user, "New-Correct-Horse-Battery-Staple-4") == user


def test_password_reset_rejects_expired_and_inactive_accounts_and_non_session_store() -> None:
    accounts = UserAccountStore(None)
    user = accounts.register("reset-boundaries@example.com", "Correct-Horse-Battery-Staple-5")
    reset = accounts.issue_action_token(user, "PASSWORD_RESET", 60)
    assert reset
    accounts._action_tokens[accounts._action_hash(reset)]["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    assert accounts.reset_password(reset, "New-Correct-Horse-Battery-Staple-5", object()) is None

    reset = accounts.issue_action_token(user, "PASSWORD_RESET", 60)
    accounts._users[user]["status"] = "SUSPENDED"
    assert accounts.reset_password(reset, "New-Correct-Horse-Battery-Staple-5", object()) is None


@pytest.mark.parametrize(
    ("provider", "subject"),
    [
        ("unknown", "subject"),
        ("google", ""),
        ("google", "x" * 513),
    ],
)
def test_external_identity_link_rejects_invalid_identity(provider: str, subject: str) -> None:
    accounts = UserAccountStore(None)
    with pytest.raises(ValueError, match="EXTERNAL_IDENTITY_INVALID"):
        accounts.link_external_identity("user", provider, subject)


def test_external_identity_linking_is_owner_scoped_and_one_provider_per_account() -> None:
    accounts = UserAccountStore(None)
    user = accounts.register("link@example.com", "Correct-Horse-Battery-Staple-6")

    with pytest.raises(ValueError, match="ACCOUNT_NOT_FOUND"):
        accounts.link_external_identity("missing", "google", "subject")

    accounts.link_external_identity(user, "Google", " subject-1 ", " Provider@Example.COM ")
    assert accounts.external_identity_user("google", "subject-1") == user
    assert accounts.security_state(user)["providers"] == ["google"]
    assert accounts._external_identities[("google", "subject-1")]["email"] == "provider@example.com"

    with pytest.raises(ValueError, match="EXTERNAL_IDENTITY_ALREADY_LINKED"):
        accounts.link_external_identity(user, "google", "subject-1")
    with pytest.raises(ValueError, match="PROVIDER_ALREADY_LINKED"):
        accounts.link_external_identity(user, "google", "subject-2")

    accounts.link_external_identity(user, "telegram", "telegram-subject")
    assert accounts.security_state(user)["providers"] == ["google", "telegram"]


@pytest.mark.parametrize(
    ("provider", "subject"),
    [
        ("unknown", "x"),
        ("google", ""),
    ],
)
def test_external_identity_lookup_invalid_inputs_are_non_enumerating(provider: str, subject: str) -> None:
    accounts = UserAccountStore(None)
    assert accounts.external_identity_user(provider, subject) is None


@pytest.mark.parametrize(
    ("provider", "purpose", "ttl", "error"),
    [
        ("unknown", "OIDC_NONCE", 300, "FEDERATED_CHALLENGE_INVALID"),
        ("google", "UNKNOWN", 300, "FEDERATED_CHALLENGE_INVALID"),
        ("google", "OIDC_NONCE", 0, "FEDERATED_CHALLENGE_TTL_INVALID"),
        ("google", "OIDC_NONCE", 901, "FEDERATED_CHALLENGE_TTL_INVALID"),
    ],
)
def test_federated_challenge_rejects_invalid_configuration(provider, purpose, ttl, error) -> None:
    accounts = UserAccountStore(None)
    with pytest.raises(ValueError, match=error):
        accounts.issue_federated_challenge(provider, purpose, ttl)


def test_federated_challenge_is_hashed_redirect_bound_expiring_and_single_use() -> None:
    accounts = UserAccountStore(None)
    raw = accounts.issue_federated_challenge(
        "Google",
        "OIDC_NONCE",
        300,
        redirect_uri="com.alpha0.app.auth://callback",
    )
    digest = accounts._action_hash(raw)
    assert raw not in accounts._federated_challenges
    assert digest in accounts._federated_challenges

    assert accounts.consume_federated_challenge("unknown", "OIDC_NONCE", raw) == (False, None)
    assert accounts.consume_federated_challenge("google", "OAUTH_STATE", raw) == (False, None)
    assert accounts.consume_federated_challenge("telegram", "OIDC_NONCE", raw) == (False, None)

    accepted, redirect = accounts.consume_federated_challenge("google", "OIDC_NONCE", raw)
    assert accepted is True
    assert redirect == "com.alpha0.app.auth://callback"
    assert accounts.consume_federated_challenge("google", "OIDC_NONCE", raw) == (False, None)

    expired = accounts.issue_federated_challenge("vk", "OAUTH_STATE", 300)
    accounts._federated_challenges[accounts._action_hash(expired)]["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    assert accounts.consume_federated_challenge("vk", "OAUTH_STATE", expired) == (False, None)


@pytest.mark.parametrize(
    ("provider", "subject"),
    [
        ("unknown", "subject"),
        ("google", ""),
        ("google", "x" * 513),
    ],
)
def test_external_account_registration_rejects_invalid_provider_identity(provider: str, subject: str) -> None:
    accounts = UserAccountStore(None)
    with pytest.raises(ValueError, match="EXTERNAL_IDENTITY_INVALID"):
        accounts.register_external_account(provider, subject, email=None, email_verified=False)


def test_external_account_registration_is_deterministic_and_never_auto_links_by_email() -> None:
    accounts = UserAccountStore(None)
    local = accounts.register("collision@example.com", "Correct-Horse-Battery-Staple-7")
    with pytest.raises(ValueError, match="ACCOUNT_LINK_REQUIRED"):
        accounts.register_external_account(
            "google",
            "google-collision",
            email="COLLISION@example.com",
            email_verified=True,
        )

    provider_user = accounts.register_external_account(
        "google",
        "google-provider-user",
        email="Person@Gmail.com",
        email_verified=True,
    )
    assert provider_user.startswith("google:")
    assert provider_user != local
    assert accounts.security_state(provider_user) == {
        "email": "person@gmail.com",
        "email_verified": True,
        "password_enabled": False,
        "providers": ["google"],
    }
    assert accounts.register_external_account(
        "google",
        "google-provider-user",
        email="different@gmail.com",
        email_verified=False,
    ) == provider_user

    anonymous_provider = accounts.register_external_account(
        "telegram",
        "telegram-provider-user",
        email=None,
        email_verified=True,
    )
    assert accounts.security_state(anonymous_provider)["email"] is None
    assert accounts.security_state(anonymous_provider)["email_verified"] is False


def test_session_scope_restriction_is_deduplicated_sorted_and_missing_safe() -> None:
    accounts = UserAccountStore(None)
    token = "opaque-access"
    store = SimpleNamespace(
        sessions={
            session_hash(token): {
                "scopes": ["game:write"],
            }
        }
    )
    accounts.restrict_session_scopes(store, token, ["game:read", "audit:read", "game:read"])
    assert store.sessions[session_hash(token)]["scopes"] == ["audit:read", "game:read"]
    accounts.restrict_session_scopes(store, "missing", ["game:read"])
