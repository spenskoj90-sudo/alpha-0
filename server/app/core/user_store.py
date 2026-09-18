from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Iterable, Literal

from sqlalchemy import text

from app.core.auth import hash_password, verify_password
from app.core.database_engine import create_service_role_engine
from app.core.security import session_hash

ActionPurpose = Literal["EMAIL_VERIFY", "PASSWORD_RESET"]
_EXTERNAL_PROVIDERS = {"google", "vk", "telegram"}


class UserAccountStore:
    def __init__(self, database_url: str | None) -> None:
        self._database_url = database_url
        self._engine = (
            create_service_role_engine(
                database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            if database_url
            else None
        )
        self._users: dict[str, dict[str, Any]] = {}
        self._action_tokens: dict[str, dict[str, Any]] = {}
        self._external_identities: dict[tuple[str, str], dict[str, str | None]] = {}
        self._lock = Lock()

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _action_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_purpose(purpose: str) -> ActionPurpose:
        if purpose not in {"EMAIL_VERIFY", "PASSWORD_RESET"}:
            raise ValueError("AUTH_ACTION_PURPOSE_INVALID")
        return purpose  # type: ignore[return-value]

    def register(self, email: str, password: str) -> str:
        email = self.normalize_email(email)
        password_hash = hash_password(password)
        user_id = email
        if self._engine:
            with self._engine.begin() as conn:
                identity = conn.execute(
                    text(
                        "INSERT INTO identities(user_handle) VALUES (:u) "
                        "ON CONFLICT (user_handle) DO UPDATE SET user_handle=EXCLUDED.user_handle RETURNING id"
                    ),
                    {"u": user_id},
                ).scalar_one()
                conn.execute(
                    text(
                        "INSERT INTO users(identity_id,email,password_hash,status,email_verified_at) "
                        "VALUES (:identity,:email,:password,'ACTIVE',NULL)"
                    ),
                    {"identity": identity, "email": email, "password": password_hash},
                )
            return user_id
        with self._lock:
            if email in self._users:
                raise ValueError("EMAIL_ALREADY_REGISTERED")
            self._users[email] = {
                "user_id": user_id,
                "email": email,
                "password_hash": password_hash,
                "status": "ACTIVE",
                "email_verified_at": None,
                "created_at": datetime.now(UTC),
            }
        return user_id

    def authenticate(self, email: str, password: str) -> str | None:
        email = self.normalize_email(email)
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT i.user_handle user_id,u.password_hash,u.status "
                        "FROM users u JOIN identities i ON i.id=u.identity_id WHERE u.email=:email"
                    ),
                    {"email": email},
                ).mappings().first()
            if (
                not row
                or row["status"] != "ACTIVE"
                or not row["password_hash"]
                or not verify_password(password, row["password_hash"])
            ):
                return None
            return row["user_id"]
        with self._lock:
            row = self._users.get(email)
        if (
            not row
            or row["status"] != "ACTIVE"
            or not row.get("password_hash")
            or not verify_password(password, row["password_hash"])
        ):
            return None
        return row["user_id"]

    def security_state(self, user_id: str) -> dict[str, Any] | None:
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT u.email,u.email_verified_at,u.password_hash "
                        "FROM users u JOIN identities i ON i.id=u.identity_id "
                        "WHERE i.user_handle=:u AND u.status='ACTIVE'"
                    ),
                    {"u": user_id},
                ).mappings().first()
                if not row:
                    return None
                providers = [
                    str(value)
                    for value in conn.execute(
                        text(
                            "SELECT provider FROM external_identities e "
                            "JOIN identities i ON i.id=e.identity_id "
                            "WHERE i.user_handle=:u ORDER BY provider"
                        ),
                        {"u": user_id},
                    ).scalars().all()
                ]
            return {
                "email": row["email"],
                "email_verified": row["email_verified_at"] is not None,
                "password_enabled": bool(row["password_hash"]),
                "providers": providers,
            }
        with self._lock:
            row = self._users.get(user_id)
            if not row or row.get("status") != "ACTIVE":
                return None
            providers = sorted(
                provider
                for (provider, _subject), binding in self._external_identities.items()
                if binding["user_id"] == user_id
            )
            return {
                "email": row["email"],
                "email_verified": row.get("email_verified_at") is not None,
                "password_enabled": bool(row.get("password_hash")),
                "providers": providers,
            }

    def issue_action_token(self, email: str, purpose: str, ttl_seconds: int) -> str | None:
        purpose_value = self._validate_purpose(purpose)
        if ttl_seconds <= 0 or ttl_seconds > 172_800:
            raise ValueError("AUTH_ACTION_TTL_INVALID")
        email = self.normalize_email(email)
        token = secrets.token_urlsafe(32)
        token_hash = self._action_hash(token)
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = conn.execute(
                    text(
                        "SELECT u.identity_id FROM users u "
                        "WHERE u.email=:email AND u.status='ACTIVE'"
                    ),
                    {"email": email},
                ).scalar_one_or_none()
                if identity_id is None:
                    return None
                conn.execute(
                    text(
                        "DELETE FROM auth_action_tokens "
                        "WHERE identity_id=:identity AND purpose=:purpose AND consumed_at IS NULL"
                    ),
                    {"identity": identity_id, "purpose": purpose_value},
                )
                conn.execute(
                    text(
                        "INSERT INTO auth_action_tokens(token_hash,identity_id,purpose,expires_at) "
                        "VALUES (:token_hash,:identity,:purpose,:expires_at)"
                    ),
                    {
                        "token_hash": token_hash,
                        "identity": identity_id,
                        "purpose": purpose_value,
                        "expires_at": expires_at,
                    },
                )
            return token
        with self._lock:
            row = self._users.get(email)
            if not row or row.get("status") != "ACTIVE":
                return None
            stale = [
                key
                for key, value in self._action_tokens.items()
                if value["user_id"] == row["user_id"]
                and value["purpose"] == purpose_value
                and value["consumed_at"] is None
            ]
            for key in stale:
                del self._action_tokens[key]
            self._action_tokens[token_hash] = {
                "user_id": row["user_id"],
                "purpose": purpose_value,
                "expires_at": expires_at,
                "consumed_at": None,
            }
        return token

    def confirm_email(self, token: str) -> bool:
        token_hash = self._action_hash(token)
        now = datetime.now(UTC)
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = conn.execute(
                    text(
                        "UPDATE auth_action_tokens SET consumed_at=now() "
                        "WHERE token_hash=:token_hash AND purpose='EMAIL_VERIFY' "
                        "AND consumed_at IS NULL AND expires_at>now() "
                        "RETURNING identity_id"
                    ),
                    {"token_hash": token_hash},
                ).scalar_one_or_none()
                if identity_id is None:
                    return False
                conn.execute(
                    text("UPDATE users SET email_verified_at=COALESCE(email_verified_at,now()),updated_at=now() WHERE identity_id=:identity"),
                    {"identity": identity_id},
                )
            return True
        with self._lock:
            action = self._action_tokens.get(token_hash)
            if (
                not action
                or action["purpose"] != "EMAIL_VERIFY"
                or action["consumed_at"] is not None
                or action["expires_at"] <= now
            ):
                return False
            action["consumed_at"] = now
            row = self._users.get(str(action["user_id"]))
            if not row:
                return False
            row["email_verified_at"] = row.get("email_verified_at") or now
        return True

    def reset_password(self, token: str, new_password: str, store: Any) -> str | None:
        token_hash = self._action_hash(token)
        new_hash = hash_password(new_password)
        now = datetime.now(UTC)
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = conn.execute(
                    text(
                        "UPDATE auth_action_tokens SET consumed_at=now() "
                        "WHERE token_hash=:token_hash AND purpose='PASSWORD_RESET' "
                        "AND consumed_at IS NULL AND expires_at>now() "
                        "RETURNING identity_id"
                    ),
                    {"token_hash": token_hash},
                ).scalar_one_or_none()
                if identity_id is None:
                    return None
                user_id = conn.execute(
                    text(
                        "UPDATE users SET password_hash=:password,updated_at=now() "
                        "WHERE identity_id=:identity AND status='ACTIVE' "
                        "RETURNING (SELECT user_handle FROM identities WHERE id=:identity)"
                    ),
                    {"password": new_hash, "identity": identity_id},
                ).scalar_one_or_none()
                if user_id is None:
                    return None
                conn.execute(
                    text(
                        "UPDATE sessions SET revoked_at=COALESCE(revoked_at,now()) "
                        "WHERE identity_id=:identity"
                    ),
                    {"identity": identity_id},
                )
            return str(user_id)
        with self._lock:
            action = self._action_tokens.get(token_hash)
            if (
                not action
                or action["purpose"] != "PASSWORD_RESET"
                or action["consumed_at"] is not None
                or action["expires_at"] <= now
            ):
                return None
            row = self._users.get(str(action["user_id"]))
            if not row or row.get("status") != "ACTIVE":
                return None
            action["consumed_at"] = now
            row["password_hash"] = new_hash
            user_id = str(row["user_id"])
        sessions = getattr(store, "sessions", None)
        if isinstance(sessions, dict):
            for record in sessions.values():
                if record.get("user_id") == user_id:
                    record["revoked"] = True
        return user_id

    def link_external_identity(
        self,
        user_id: str,
        provider: str,
        provider_subject: str,
        email_at_link_time: str | None = None,
    ) -> None:
        provider = provider.strip().lower()
        subject = provider_subject.strip()
        if provider not in _EXTERNAL_PROVIDERS or not subject or len(subject) > 512:
            raise ValueError("EXTERNAL_IDENTITY_INVALID")
        normalized_email = self.normalize_email(email_at_link_time) if email_at_link_time else None
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = conn.execute(
                    text("SELECT id FROM identities WHERE user_handle=:u"),
                    {"u": user_id},
                ).scalar_one_or_none()
                if identity_id is None:
                    raise ValueError("ACCOUNT_NOT_FOUND")
                conn.execute(
                    text(
                        "INSERT INTO external_identities(identity_id,provider,provider_subject,email_at_link_time) "
                        "VALUES (:identity,:provider,:subject,:email)"
                    ),
                    {
                        "identity": identity_id,
                        "provider": provider,
                        "subject": subject,
                        "email": normalized_email,
                    },
                )
            return
        with self._lock:
            if user_id not in self._users:
                raise ValueError("ACCOUNT_NOT_FOUND")
            key = (provider, subject)
            if key in self._external_identities:
                raise ValueError("EXTERNAL_IDENTITY_ALREADY_LINKED")
            if any(
                binding["user_id"] == user_id and existing_provider == provider
                for (existing_provider, _), binding in self._external_identities.items()
            ):
                raise ValueError("PROVIDER_ALREADY_LINKED")
            self._external_identities[key] = {
                "user_id": user_id,
                "email": normalized_email,
            }

    def external_identity_user(self, provider: str, provider_subject: str) -> str | None:
        provider = provider.strip().lower()
        subject = provider_subject.strip()
        if provider not in _EXTERNAL_PROVIDERS or not subject:
            return None
        if self._engine:
            with self._engine.begin() as conn:
                return conn.execute(
                    text(
                        "SELECT i.user_handle FROM external_identities e "
                        "JOIN identities i ON i.id=e.identity_id "
                        "WHERE e.provider=:provider AND e.provider_subject=:subject"
                    ),
                    {"provider": provider, "subject": subject},
                ).scalar_one_or_none()
        with self._lock:
            binding = self._external_identities.get((provider, subject))
            return str(binding["user_id"]) if binding else None

    def restrict_session_scopes(self, store: Any, access_token: str, scopes: Iterable[str]) -> None:
        normalized = sorted(set(scopes))
        if self._engine:
            with self._engine.begin() as conn:
                conn.execute(
                    text("UPDATE sessions SET scopes_json=CAST(:scopes AS jsonb) WHERE session_hash=:session_hash"),
                    {"scopes": json.dumps(normalized), "session_hash": session_hash(access_token)},
                )
            return
        record = store.sessions.get(session_hash(access_token))
        if record is not None:
            record["scopes"] = normalized
