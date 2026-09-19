from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from threading import Lock
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

from app.core.database_engine import create_service_role_engine
from app.core.totp import matching_totp_counter

_MFA_KEY_ENV = "SENTINEL_ACCOUNT_MFA_KEY"
_MFA_CHALLENGE_TTL_SECONDS = 300
_RECOVERY_CODE_COUNT = 10


class AccountMfaConfigurationError(RuntimeError):
    pass


class AccountMfaService:
    """Server-authoritative TOTP/recovery-code state.

    TOTP seeds are recoverable credentials and are therefore encrypted at rest
    with an environment-injected Fernet key. Login challenges and recovery
    codes are persisted only as SHA-256 digests.
    """

    def __init__(self, database_url: str | None) -> None:
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
        self._memory: dict[str, dict[str, object]] = {}
        self._recovery: dict[str, dict[str, bool]] = {}
        self._challenges: dict[str, dict[str, object]] = {}
        self._lock = Lock()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_recovery_code(code: str) -> str:
        return "".join(ch for ch in code.upper() if ch.isalnum())

    @classmethod
    def _recovery_digest(cls, code: str) -> str:
        return cls._digest(cls._normalize_recovery_code(code))

    @staticmethod
    def _cipher() -> Fernet:
        raw = os.getenv(_MFA_KEY_ENV, "").strip()
        if not raw:
            raise AccountMfaConfigurationError("ACCOUNT_MFA_KEY_NOT_CONFIGURED")
        try:
            return Fernet(raw.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise AccountMfaConfigurationError("ACCOUNT_MFA_KEY_INVALID") from exc

    @classmethod
    def _encrypt_secret(cls, secret: str) -> str:
        return cls._cipher().encrypt(secret.encode("ascii")).decode("ascii")

    @classmethod
    def _decrypt_secret(cls, ciphertext: str) -> str:
        try:
            return cls._cipher().decrypt(ciphertext.encode("ascii")).decode("ascii")
        except InvalidToken as exc:
            raise AccountMfaConfigurationError("ACCOUNT_MFA_SECRET_UNREADABLE") from exc

    @staticmethod
    def _new_totp_secret() -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    @staticmethod
    def _new_recovery_codes() -> list[str]:
        values: list[str] = []
        for _ in range(_RECOVERY_CODE_COUNT):
            raw = base64.b32encode(secrets.token_bytes(12)).decode("ascii").rstrip("=")
            values.append("-".join(raw[index : index + 4] for index in range(0, len(raw), 4)))
        return values

    @staticmethod
    def _otpauth_uri(secret: str, account_label: str) -> str:
        label = quote(f"SENTINEL:{account_label}", safe="")
        issuer = quote("SENTINEL", safe="")
        return (
            f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
            "&algorithm=SHA1&digits=6&period=30"
        )

    @staticmethod
    def _identity_id(conn, user_id: str):
        return conn.execute(
            text("SELECT id FROM identities WHERE user_handle=:user_id"),
            {"user_id": user_id},
        ).scalar_one_or_none()

    def state(self, user_id: str) -> dict[str, int | bool]:
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT m.enabled_at, "
                        "(SELECT COUNT(*) FROM account_mfa_recovery_codes r "
                        " WHERE r.identity_id=m.identity_id AND r.consumed_at IS NULL) recovery_count "
                        "FROM account_mfa_totp m JOIN identities i ON i.id=m.identity_id "
                        "WHERE i.user_handle=:user_id"
                    ),
                    {"user_id": user_id},
                ).mappings().first()
            enabled = bool(row and row["enabled_at"] is not None)
            return {
                "enabled": enabled,
                "recovery_codes_remaining": int(row["recovery_count"]) if enabled and row else 0,
            }
        with self._lock:
            record = self._memory.get(user_id)
            enabled = bool(record and record.get("enabled_at") is not None)
            remaining = sum(1 for consumed in self._recovery.get(user_id, {}).values() if not consumed) if enabled else 0
            return {"enabled": enabled, "recovery_codes_remaining": remaining}

    def begin_enrollment(self, user_id: str, account_label: str) -> dict[str, str]:
        secret = self._new_totp_secret()
        ciphertext = self._encrypt_secret(secret)
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = self._identity_id(conn, user_id)
                if identity_id is None:
                    raise ValueError("ACCOUNT_NOT_FOUND")
                existing = conn.execute(
                    text("SELECT enabled_at FROM account_mfa_totp WHERE identity_id=:identity"),
                    {"identity": identity_id},
                ).mappings().first()
                if existing and existing["enabled_at"] is not None:
                    raise ValueError("MFA_ALREADY_ENABLED")
                conn.execute(
                    text(
                        "INSERT INTO account_mfa_totp(identity_id,secret_ciphertext,enabled_at,last_totp_counter) "
                        "VALUES (:identity,:ciphertext,NULL,NULL) "
                        "ON CONFLICT (identity_id) DO UPDATE SET "
                        "secret_ciphertext=EXCLUDED.secret_ciphertext,enabled_at=NULL,last_totp_counter=NULL,updated_at=now()"
                    ),
                    {"identity": identity_id, "ciphertext": ciphertext},
                )
                conn.execute(
                    text("DELETE FROM account_mfa_recovery_codes WHERE identity_id=:identity"),
                    {"identity": identity_id},
                )
                conn.execute(
                    text("DELETE FROM account_mfa_login_challenges WHERE identity_id=:identity"),
                    {"identity": identity_id},
                )
        else:
            with self._lock:
                existing = self._memory.get(user_id)
                if existing and existing.get("enabled_at") is not None:
                    raise ValueError("MFA_ALREADY_ENABLED")
                self._memory[user_id] = {
                    "secret_ciphertext": ciphertext,
                    "enabled_at": None,
                    "last_totp_counter": None,
                }
                self._recovery.pop(user_id, None)
                for challenge_hash in [
                    key for key, value in self._challenges.items() if value["user_id"] == user_id
                ]:
                    del self._challenges[challenge_hash]
        return {"secret": secret, "otpauth_uri": self._otpauth_uri(secret, account_label)}

    def confirm_enrollment(self, user_id: str, code: str) -> list[str] | None:
        recovery_codes = self._new_recovery_codes()
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT m.identity_id,m.secret_ciphertext,m.enabled_at "
                        "FROM account_mfa_totp m JOIN identities i ON i.id=m.identity_id "
                        "WHERE i.user_handle=:user_id FOR UPDATE OF m"
                    ),
                    {"user_id": user_id},
                ).mappings().first()
                if not row or row["enabled_at"] is not None:
                    return None
                secret = self._decrypt_secret(str(row["secret_ciphertext"]))
                counter = matching_totp_counter(secret, code)
                if counter is None:
                    return None
                identity_id = row["identity_id"]
                conn.execute(
                    text(
                        "UPDATE account_mfa_totp SET enabled_at=now(),last_totp_counter=:counter,updated_at=now() "
                        "WHERE identity_id=:identity"
                    ),
                    {"counter": counter, "identity": identity_id},
                )
                conn.execute(
                    text("DELETE FROM account_mfa_recovery_codes WHERE identity_id=:identity"),
                    {"identity": identity_id},
                )
                for recovery_code in recovery_codes:
                    conn.execute(
                        text(
                            "INSERT INTO account_mfa_recovery_codes(identity_id,code_hash) "
                            "VALUES (:identity,:code_hash)"
                        ),
                        {"identity": identity_id, "code_hash": self._recovery_digest(recovery_code)},
                    )
            return recovery_codes
        with self._lock:
            record = self._memory.get(user_id)
            if not record or record.get("enabled_at") is not None:
                return None
            secret = self._decrypt_secret(str(record["secret_ciphertext"]))
            counter = matching_totp_counter(secret, code)
            if counter is None:
                return None
            record["enabled_at"] = datetime.now(UTC)
            record["last_totp_counter"] = counter
            self._recovery[user_id] = {
                self._recovery_digest(recovery_code): False for recovery_code in recovery_codes
            }
        return recovery_codes

    def issue_login_challenge(
        self,
        user_id: str,
        ttl_seconds: int = _MFA_CHALLENGE_TTL_SECONDS,
    ) -> tuple[str, datetime] | None:
        if not self.state(user_id)["enabled"]:
            return None
        token = secrets.token_urlsafe(32)
        challenge_hash = self._digest(token)
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        if self._engine:
            with self._engine.begin() as conn:
                identity_id = self._identity_id(conn, user_id)
                if identity_id is None:
                    return None
                conn.execute(
                    text(
                        "DELETE FROM account_mfa_login_challenges "
                        "WHERE identity_id=:identity AND (expires_at<=now() OR consumed_at IS NOT NULL)"
                    ),
                    {"identity": identity_id},
                )
                conn.execute(
                    text(
                        "INSERT INTO account_mfa_login_challenges(challenge_hash,identity_id,expires_at) "
                        "VALUES (:challenge_hash,:identity,:expires_at)"
                    ),
                    {
                        "challenge_hash": challenge_hash,
                        "identity": identity_id,
                        "expires_at": expires_at,
                    },
                )
        else:
            now = datetime.now(UTC)
            with self._lock:
                for key in [
                    key for key, value in self._challenges.items()
                    if value["expires_at"] <= now or value.get("consumed_at") is not None
                ]:
                    del self._challenges[key]
                self._challenges[challenge_hash] = {
                    "user_id": user_id,
                    "expires_at": expires_at,
                    "consumed_at": None,
                }
        return token, expires_at

    def _consume_recovery_db(self, conn, identity_id, code: str) -> bool:
        result = conn.execute(
            text(
                "UPDATE account_mfa_recovery_codes SET consumed_at=now() "
                "WHERE identity_id=:identity AND code_hash=:code_hash AND consumed_at IS NULL "
                "RETURNING code_hash"
            ),
            {"identity": identity_id, "code_hash": self._recovery_digest(code)},
        ).scalar_one_or_none()
        return result is not None

    def complete_login_challenge(self, token: str, code: str) -> str | None:
        challenge_hash = self._digest(token)
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT c.identity_id,i.user_handle,m.secret_ciphertext,m.last_totp_counter "
                        "FROM account_mfa_login_challenges c "
                        "JOIN identities i ON i.id=c.identity_id "
                        "JOIN account_mfa_totp m ON m.identity_id=c.identity_id "
                        "WHERE c.challenge_hash=:challenge_hash AND c.consumed_at IS NULL "
                        "AND c.expires_at>now() AND m.enabled_at IS NOT NULL "
                        "FOR UPDATE OF c,m"
                    ),
                    {"challenge_hash": challenge_hash},
                ).mappings().first()
                if not row:
                    return None
                secret = self._decrypt_secret(str(row["secret_ciphertext"]))
                last_counter = int(row["last_totp_counter"]) if row["last_totp_counter"] is not None else None
                counter = matching_totp_counter(secret, code, last_counter=last_counter)
                accepted = counter is not None
                if accepted:
                    conn.execute(
                        text(
                            "UPDATE account_mfa_totp SET last_totp_counter=:counter,updated_at=now() "
                            "WHERE identity_id=:identity"
                        ),
                        {"counter": counter, "identity": row["identity_id"]},
                    )
                else:
                    accepted = self._consume_recovery_db(conn, row["identity_id"], code)
                if not accepted:
                    return None
                conn.execute(
                    text(
                        "UPDATE account_mfa_login_challenges SET consumed_at=now() "
                        "WHERE challenge_hash=:challenge_hash"
                    ),
                    {"challenge_hash": challenge_hash},
                )
                return str(row["user_handle"])

        now = datetime.now(UTC)
        with self._lock:
            challenge = self._challenges.get(challenge_hash)
            if (
                not challenge
                or challenge.get("consumed_at") is not None
                or challenge["expires_at"] <= now
            ):
                return None
            user_id = str(challenge["user_id"])
            record = self._memory.get(user_id)
            if not record or record.get("enabled_at") is None:
                return None
            secret = self._decrypt_secret(str(record["secret_ciphertext"]))
            last_counter = record.get("last_totp_counter")
            counter = matching_totp_counter(
                secret,
                code,
                last_counter=int(last_counter) if last_counter is not None else None,
            )
            accepted = counter is not None
            if accepted:
                record["last_totp_counter"] = counter
            else:
                digest = self._recovery_digest(code)
                recovery = self._recovery.get(user_id, {})
                if digest in recovery and recovery[digest] is False:
                    recovery[digest] = True
                    accepted = True
            if not accepted:
                return None
            challenge["consumed_at"] = now
            return user_id

    def disable(self, user_id: str, code: str) -> bool:
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT m.identity_id,m.secret_ciphertext,m.last_totp_counter "
                        "FROM account_mfa_totp m JOIN identities i ON i.id=m.identity_id "
                        "WHERE i.user_handle=:user_id AND m.enabled_at IS NOT NULL FOR UPDATE OF m"
                    ),
                    {"user_id": user_id},
                ).mappings().first()
                if not row:
                    return False
                secret = self._decrypt_secret(str(row["secret_ciphertext"]))
                last_counter = int(row["last_totp_counter"]) if row["last_totp_counter"] is not None else None
                counter = matching_totp_counter(secret, code, last_counter=last_counter)
                accepted = counter is not None or self._consume_recovery_db(conn, row["identity_id"], code)
                if not accepted:
                    return False
                identity_id = row["identity_id"]
                conn.execute(
                    text("DELETE FROM account_mfa_login_challenges WHERE identity_id=:identity"),
                    {"identity": identity_id},
                )
                conn.execute(
                    text("DELETE FROM account_mfa_recovery_codes WHERE identity_id=:identity"),
                    {"identity": identity_id},
                )
                conn.execute(
                    text("DELETE FROM account_mfa_totp WHERE identity_id=:identity"),
                    {"identity": identity_id},
                )
            return True
        with self._lock:
            record = self._memory.get(user_id)
            if not record or record.get("enabled_at") is None:
                return False
            secret = self._decrypt_secret(str(record["secret_ciphertext"]))
            last_counter = record.get("last_totp_counter")
            counter = matching_totp_counter(
                secret,
                code,
                last_counter=int(last_counter) if last_counter is not None else None,
            )
            accepted = counter is not None
            if not accepted:
                digest = self._recovery_digest(code)
                recovery = self._recovery.get(user_id, {})
                accepted = digest in recovery and recovery[digest] is False
            if not accepted:
                return False
            self._memory.pop(user_id, None)
            self._recovery.pop(user_id, None)
            for key in [
                key for key, value in self._challenges.items() if value["user_id"] == user_id
            ]:
                del self._challenges[key]
            return True

    def rotate_recovery_codes(self, user_id: str, code: str) -> list[str] | None:
        replacement = self._new_recovery_codes()
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT m.identity_id,m.secret_ciphertext,m.last_totp_counter "
                        "FROM account_mfa_totp m JOIN identities i ON i.id=m.identity_id "
                        "WHERE i.user_handle=:user_id AND m.enabled_at IS NOT NULL FOR UPDATE OF m"
                    ),
                    {"user_id": user_id},
                ).mappings().first()
                if not row:
                    return None
                secret = self._decrypt_secret(str(row["secret_ciphertext"]))
                last_counter = int(row["last_totp_counter"]) if row["last_totp_counter"] is not None else None
                counter = matching_totp_counter(secret, code, last_counter=last_counter)
                if counter is None:
                    return None
                conn.execute(
                    text(
                        "UPDATE account_mfa_totp SET last_totp_counter=:counter,updated_at=now() "
                        "WHERE identity_id=:identity"
                    ),
                    {"counter": counter, "identity": row["identity_id"]},
                )
                conn.execute(
                    text("DELETE FROM account_mfa_recovery_codes WHERE identity_id=:identity"),
                    {"identity": row["identity_id"]},
                )
                for recovery_code in replacement:
                    conn.execute(
                        text(
                            "INSERT INTO account_mfa_recovery_codes(identity_id,code_hash) "
                            "VALUES (:identity,:code_hash)"
                        ),
                        {"identity": row["identity_id"], "code_hash": self._recovery_digest(recovery_code)},
                    )
            return replacement
        with self._lock:
            record = self._memory.get(user_id)
            if not record or record.get("enabled_at") is None:
                return None
            secret = self._decrypt_secret(str(record["secret_ciphertext"]))
            last_counter = record.get("last_totp_counter")
            counter = matching_totp_counter(
                secret,
                code,
                last_counter=int(last_counter) if last_counter is not None else None,
            )
            if counter is None:
                return None
            record["last_totp_counter"] = counter
            self._recovery[user_id] = {
                self._recovery_digest(recovery_code): False for recovery_code in replacement
            }
        return replacement
