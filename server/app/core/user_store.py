from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any

from sqlalchemy import create_engine, text

from app.core.auth import hash_password, verify_password


class UserAccountStore:
    def __init__(self, database_url: str | None) -> None:
        self._database_url = database_url
        self._engine = create_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=10) if database_url else None
        self._users: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def register(self, email: str, password: str) -> str:
        email = self.normalize_email(email)
        password_hash = hash_password(password)
        user_id = email
        if self._engine:
            with self._engine.begin() as conn:
                identity = conn.execute(
                    text("INSERT INTO identities(user_handle) VALUES (:u) ON CONFLICT (user_handle) DO UPDATE SET user_handle=EXCLUDED.user_handle RETURNING id"),
                    {"u": user_id},
                ).scalar_one()
                try:
                    conn.execute(
                        text("INSERT INTO users(id,identity_id,email,password_hash,status) VALUES (:id,:identity,:email,:password,'ACTIVE')"),
                        {"id": identity, "identity": identity, "email": email, "password": password_hash},
                    )
                except Exception:
                    raise
            return user_id
        with self._lock:
            if email in self._users:
                raise ValueError("EMAIL_ALREADY_REGISTERED")
            self._users[email] = {"user_id": user_id, "email": email, "password_hash": password_hash, "status": "ACTIVE", "created_at": datetime.now(UTC)}
        return user_id

    def authenticate(self, email: str, password: str) -> str | None:
        email = self.normalize_email(email)
        if self._engine:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text("SELECT i.user_handle user_id,u.password_hash,u.status FROM users u JOIN identities i ON i.id=u.identity_id WHERE u.email=:email"),
                    {"email": email},
                ).mappings().first()
            if not row or row["status"] != "ACTIVE" or not verify_password(password, row["password_hash"]):
                return None
            return row["user_id"]
        with self._lock:
            row = self._users.get(email)
        if not row or row["status"] != "ACTIVE" or not verify_password(password, row["password_hash"]):
            return None
        return row["user_id"]
