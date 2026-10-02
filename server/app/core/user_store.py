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
from app.core.email_codes import (DUMMY_CODE_HASH, EMAIL_CODE_MAX_ATTEMPTS, EMAIL_CODE_PATTERN, EMAIL_CODE_REQUESTS_PER_HOUR, EMAIL_CODE_TTL_SECONDS, normalize_action_code)

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
        self._federated_challenges: dict[str, dict[str, Any]] = {}
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

    def issue_action_code(self, email: str, purpose: str, ttl_seconds: int = EMAIL_CODE_TTL_SECONDS) -> str | None:
        purpose_value = self._validate_purpose(purpose)
        if not 0 < ttl_seconds <= EMAIL_CODE_TTL_SECONDS:
            raise ValueError("AUTH_ACTION_TTL_INVALID")
        email = self.normalize_email(email)
        code = f"{secrets.randbelow(100_000_000):08d}"
        code_hash = hash_password(code)
        selector = self._action_hash(secrets.token_urlsafe(32))
        now = datetime.now(UTC)
        if self._engine:
            with self._engine.begin() as conn:
                identity = conn.execute(text("SELECT identity_id FROM users WHERE email=:email AND status='ACTIVE' FOR UPDATE"), {"email": email}).scalar_one_or_none()
                if identity is None:
                    return None
                count = conn.execute(text("SELECT count(*) FROM auth_action_tokens WHERE identity_id=:identity AND purpose=:purpose AND code_hash IS NOT NULL AND created_at>:since"), {"identity": identity, "purpose": purpose_value, "since": now - timedelta(hours=1)}).scalar_one()
                if count >= EMAIL_CODE_REQUESTS_PER_HOUR:
                    return None
                conn.execute(text("UPDATE auth_action_tokens SET consumed_at=:now WHERE identity_id=:identity AND purpose=:purpose AND consumed_at IS NULL"), {"identity": identity, "purpose": purpose_value, "now": now})
                conn.execute(text("INSERT INTO auth_action_tokens(token_hash,identity_id,purpose,expires_at,code_hash,created_at) VALUES (:selector,:identity,:purpose,:expires,:code_hash,:now)"), {"selector": selector, "identity": identity, "purpose": purpose_value, "expires": now + timedelta(seconds=ttl_seconds), "code_hash": code_hash, "now": now})
            return code
        with self._lock:
            user = next((u for u in self._users.values() if u.get("email") == email and u.get("status") == "ACTIVE"), None)
            if user is None:
                return None
            history = [a for a in self._action_tokens.values() if a["user_id"] == user["user_id"] and a["purpose"] == purpose_value]
            if sum(bool(a.get("code_hash")) and a.get("created_at", now) > now - timedelta(hours=1) for a in history) >= EMAIL_CODE_REQUESTS_PER_HOUR:
                return None
            for action in history:
                if action["consumed_at"] is None:
                    action["consumed_at"] = now
            self._action_tokens[selector] = {"user_id": user["user_id"], "purpose": purpose_value, "expires_at": now + timedelta(seconds=ttl_seconds), "created_at": now, "consumed_at": None, "code_hash": code_hash, "failed_attempts": 0}
        return code

    def _consume_database_code(self, conn: Any, email: str | None, purpose: str, code: str) -> Any:
        # The users row serializes issue/consume/budget operations across connections and workers.
        identity = conn.execute(text("SELECT identity_id FROM users WHERE email=:email AND status='ACTIVE' FOR UPDATE"), {"email": self.normalize_email(email or "")}).scalar_one_or_none()
        action = conn.execute(text("SELECT token_hash,code_hash FROM auth_action_tokens WHERE identity_id=:identity AND purpose=:purpose AND code_hash IS NOT NULL AND consumed_at IS NULL AND expires_at>now() AND failed_attempts<:max_attempts ORDER BY created_at DESC LIMIT 1 FOR UPDATE"), {"identity": identity, "purpose": purpose, "max_attempts": EMAIL_CODE_MAX_ATTEMPTS}).mappings().first() if identity is not None else None
        valid = verify_password(code, action["code_hash"] if action else DUMMY_CODE_HASH)
        if not action:
            return None
        if not valid:
            conn.execute(text("UPDATE auth_action_tokens SET failed_attempts=failed_attempts+1,consumed_at=CASE WHEN failed_attempts+1>=:max_attempts THEN now() ELSE consumed_at END WHERE token_hash=:selector"), {"selector": action["token_hash"], "max_attempts": EMAIL_CODE_MAX_ATTEMPTS})
            return None
        conn.execute(text("UPDATE auth_action_tokens SET consumed_at=now() WHERE token_hash=:selector"), {"selector": action["token_hash"]})
        return identity

    def _consume_memory_code(self, email: str | None, purpose: str, code: str) -> dict[str, Any] | None:
        # Called only while holding self._lock; failed attempts survive resends/process boundaries in DB.
        now = datetime.now(UTC)
        user = next((u for u in self._users.values() if u.get("email") == self.normalize_email(email or "") and u.get("status") == "ACTIVE"), None)
        actions = [a for a in self._action_tokens.values() if user and a["user_id"] == user["user_id"] and a["purpose"] == purpose and a.get("code_hash") and a["consumed_at"] is None and a["expires_at"] > now and a["failed_attempts"] < EMAIL_CODE_MAX_ATTEMPTS]
        action = max(actions, key=lambda a: a["created_at"]) if actions else None
        valid = verify_password(code, action["code_hash"] if action else DUMMY_CODE_HASH)
        if not action:
            return None
        if not valid:
            action["failed_attempts"] += 1
            if action["failed_attempts"] >= EMAIL_CODE_MAX_ATTEMPTS:
                action["consumed_at"] = now
            return None
        action["consumed_at"] = now
        return user

    def confirm_email(self, token: str, email: str | None = None) -> bool:
        token = normalize_action_code(token)
        numeric = bool(EMAIL_CODE_PATTERN.fullmatch(token))
        token_hash = self._action_hash(token)
        now = datetime.now(UTC)
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = self._consume_database_code(conn, email, "EMAIL_VERIFY", token) if numeric else conn.execute(
                    text(
                        "UPDATE auth_action_tokens SET consumed_at=now() "
                        "WHERE token_hash=:token_hash AND purpose='EMAIL_VERIFY' "
                        "AND code_hash IS NULL AND consumed_at IS NULL AND expires_at>now() "
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
            if numeric:
                row = self._consume_memory_code(email, "EMAIL_VERIFY", token)
                if row is None:
                    return False
                row["email_verified_at"] = row.get("email_verified_at") or now
                return True
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

    def reset_password(self, token: str, new_password: str, store: Any, email: str | None = None) -> str | None:
        token = normalize_action_code(token)
        numeric = bool(EMAIL_CODE_PATTERN.fullmatch(token))
        token_hash = self._action_hash(token)
        new_hash = hash_password(new_password)
        now = datetime.now(UTC)
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = self._consume_database_code(conn, email, "PASSWORD_RESET", token) if numeric else conn.execute(
                    text(
                        "UPDATE auth_action_tokens SET consumed_at=now() "
                        "WHERE token_hash=:token_hash AND purpose='PASSWORD_RESET' "
                        "AND code_hash IS NULL AND consumed_at IS NULL AND expires_at>now() "
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
            if numeric:
                row = self._consume_memory_code(email, "PASSWORD_RESET", token)
                if row is None:
                    return None
            else:
                action = self._action_tokens.get(token_hash)
                if (not action or action["purpose"] != "PASSWORD_RESET" or action["consumed_at"] is not None or action["expires_at"] <= now):
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
                subject_owner = conn.execute(
                    text(
                        "SELECT i.user_handle FROM external_identities e "
                        "JOIN identities i ON i.id=e.identity_id "
                        "WHERE e.provider=:provider AND e.provider_subject=:subject"
                    ),
                    {"provider": provider, "subject": subject},
                ).scalar_one_or_none()
                if subject_owner is not None:
                    raise ValueError("EXTERNAL_IDENTITY_ALREADY_LINKED")
                provider_exists = conn.execute(
                    text(
                        "SELECT 1 FROM external_identities "
                        "WHERE identity_id=:identity AND provider=:provider"
                    ),
                    {"identity": identity_id, "provider": provider},
                ).scalar_one_or_none()
                if provider_exists is not None:
                    raise ValueError("PROVIDER_ALREADY_LINKED")
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

    def issue_federated_challenge(
        self,
        provider: str,
        purpose: str,
        ttl_seconds: int = 300,
        redirect_uri: str | None = None,
    ) -> str:
        provider = provider.strip().lower()
        if provider not in _EXTERNAL_PROVIDERS or purpose not in {"OIDC_NONCE", "OAUTH_STATE"}:
            raise ValueError("FEDERATED_CHALLENGE_INVALID")
        if ttl_seconds <= 0 or ttl_seconds > 900:
            raise ValueError("FEDERATED_CHALLENGE_TTL_INVALID")
        token = secrets.token_urlsafe(32)
        token_hash = self._action_hash(token)
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        if self._engine:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO federated_auth_challenges"
                        "(challenge_hash,provider,purpose,redirect_uri,expires_at) "
                        "VALUES (:challenge_hash,:provider,:purpose,:redirect_uri,:expires_at)"
                    ),
                    {
                        "challenge_hash": token_hash,
                        "provider": provider,
                        "purpose": purpose,
                        "redirect_uri": redirect_uri,
                        "expires_at": expires_at,
                    },
                )
            return token
        with self._lock:
            self._federated_challenges[token_hash] = {
                "provider": provider,
                "purpose": purpose,
                "redirect_uri": redirect_uri,
                "expires_at": expires_at,
                "consumed_at": None,
            }
        return token

    def consume_federated_challenge(
        self,
        provider: str,
        purpose: str,
        token: str,
    ) -> tuple[bool, str | None]:
        provider = provider.strip().lower()
        token_hash = self._action_hash(token)
        now = datetime.now(UTC)
        if provider not in _EXTERNAL_PROVIDERS or purpose not in {"OIDC_NONCE", "OAUTH_STATE"}:
            return False, None
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "UPDATE federated_auth_challenges SET consumed_at=now() "
                        "WHERE challenge_hash=:challenge_hash AND provider=:provider "
                        "AND purpose=:purpose AND consumed_at IS NULL AND expires_at>now() "
                        "RETURNING redirect_uri"
                    ),
                    {
                        "challenge_hash": token_hash,
                        "provider": provider,
                        "purpose": purpose,
                    },
                ).mappings().first()
            if row is None:
                return False, None
            return True, row["redirect_uri"]
        with self._lock:
            row = self._federated_challenges.get(token_hash)
            if (
                not row
                or row["provider"] != provider
                or row["purpose"] != purpose
                or row["consumed_at"] is not None
                or row["expires_at"] <= now
            ):
                return False, None
            row["consumed_at"] = now
            return True, row.get("redirect_uri")

    def register_external_account(
        self,
        provider: str,
        provider_subject: str,
        *,
        email: str | None,
        email_verified: bool,
    ) -> str:
        provider = provider.strip().lower()
        subject = provider_subject.strip()
        if provider not in _EXTERNAL_PROVIDERS or not subject or len(subject) > 512:
            raise ValueError("EXTERNAL_IDENTITY_INVALID")
        normalized_email = self.normalize_email(email) if email else None
        existing = self.external_identity_user(provider, subject)
        if existing:
            return existing
        user_id = f"{provider}:{hashlib.sha256((provider + chr(0) + subject).encode()).hexdigest()[:48]}"
        if self._engine:
            with self._engine.begin() as conn:
                if normalized_email:
                    local_owner = conn.execute(
                        text(
                            "SELECT i.user_handle FROM users u "
                            "JOIN identities i ON i.id=u.identity_id "
                            "WHERE u.email=:email"
                        ),
                        {"email": normalized_email},
                    ).scalar_one_or_none()
                    if local_owner:
                        raise ValueError("ACCOUNT_LINK_REQUIRED")
                identity_id = conn.execute(
                    text(
                        "INSERT INTO identities(user_handle) VALUES (:user_id) "
                        "ON CONFLICT (user_handle) DO UPDATE SET user_handle=EXCLUDED.user_handle "
                        "RETURNING id"
                    ),
                    {"user_id": user_id},
                ).scalar_one()
                has_user = conn.execute(
                    text("SELECT 1 FROM users WHERE identity_id=:identity"),
                    {"identity": identity_id},
                ).scalar_one_or_none()
                if has_user is None:
                    conn.execute(
                        text(
                            "INSERT INTO users(identity_id,email,password_hash,status,email_verified_at) "
                            "VALUES (:identity,:email,NULL,'ACTIVE',"
                            "CASE WHEN :verified THEN now() ELSE NULL END)"
                        ),
                        {
                            "identity": identity_id,
                            "email": normalized_email,
                            "verified": bool(email_verified and normalized_email),
                        },
                    )
                conn.execute(
                    text(
                        "INSERT INTO external_identities"
                        "(identity_id,provider,provider_subject,email_at_link_time) "
                        "VALUES (:identity,:provider,:subject,:email) "
                        "ON CONFLICT (provider,provider_subject) DO NOTHING"
                    ),
                    {
                        "identity": identity_id,
                        "provider": provider,
                        "subject": subject,
                        "email": normalized_email,
                    },
                )
                bound_user = conn.execute(
                    text(
                        "SELECT i.user_handle FROM external_identities e "
                        "JOIN identities i ON i.id=e.identity_id "
                        "WHERE e.provider=:provider AND e.provider_subject=:subject"
                    ),
                    {"provider": provider, "subject": subject},
                ).scalar_one()
            if str(bound_user) != user_id:
                raise ValueError("EXTERNAL_IDENTITY_ALREADY_LINKED")
            return user_id
        with self._lock:
            binding = self._external_identities.get((provider, subject))
            if binding:
                return str(binding["user_id"])
            if normalized_email and any(
                row.get("email") == normalized_email for row in self._users.values()
            ):
                raise ValueError("ACCOUNT_LINK_REQUIRED")
            if user_id not in self._users:
                self._users[user_id] = {
                    "user_id": user_id,
                    "email": normalized_email,
                    "password_hash": None,
                    "status": "ACTIVE",
                    "email_verified_at": datetime.now(UTC)
                    if email_verified and normalized_email
                    else None,
                    "created_at": datetime.now(UTC),
                }
            self._external_identities[(provider, subject)] = {
                "user_id": user_id,
                "email": normalized_email,
            }
        return user_id

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
