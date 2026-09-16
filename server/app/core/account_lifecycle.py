from __future__ import annotations

import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.core.auth import hash_password, verify_password
from app.core.store import MemoryStore, PostgresStore
from app.core.user_store import UserAccountStore

_MAX_EXPORT_ROWS = 5000
_REDACTED_REPORT_TITLE = "Erased account report"
_REDACTED_REPORT_DESCRIPTION = "[redacted after account erasure]"


class AccountLifecycleService:
    """Authenticated account export and pseudonymizing erasure.

    Durable security/game evidence is intentionally retained under an opaque
    tombstone identity because game_events use RESTRICT semantics. Login PII,
    active credentials, device access and quality-report free text are removed.
    """

    def __init__(self, store: Any, user_store: UserAccountStore) -> None:
        self.store = store
        self.user_store = user_store

    def export(self, user_id: str) -> dict[str, Any]:
        if isinstance(self.store, MemoryStore):
            return self._export_memory(user_id)
        if isinstance(self.store, PostgresStore):
            return self._export_postgres(user_id)
        raise RuntimeError("ACCOUNT_LIFECYCLE_STORE_UNSUPPORTED")

    def erase(self, user_id: str, password: str) -> dict[str, Any]:
        if isinstance(self.store, MemoryStore):
            return self._erase_memory(user_id, password)
        if isinstance(self.store, PostgresStore):
            return self._erase_postgres(user_id, password)
        raise RuntimeError("ACCOUNT_LIFECYCLE_STORE_UNSUPPORTED")

    def _export_memory(self, user_id: str) -> dict[str, Any]:
        with self.user_store._lock:
            account = self.user_store._users.get(user_id)
            if not account or account.get("status") != "ACTIVE":
                raise ValueError("ACCOUNT_NOT_FOUND")
            profile = {
                "user_id": user_id,
                "email": account["email"],
                "status": account["status"],
                "created_at": account["created_at"],
            }
        with self.store.lock:
            sections = {
                "devices": [self._safe_device(item) for item in self.store.devices.values() if item.get("user_id") == user_id],
                "entitlements": [dict(item) for item in self.store.list_entitlements(user_id)],
                "subscriptions": [dict(item) for item in self.store.subscriptions.values() if item.get("user_id") == user_id],
                "characters": [dict(item) for item in self.store.characters.values() if item.get("user_id") == user_id],
                "audit": [dict(item) for item in self.store.audit if item.get("actor_user_id") == user_id],
                "events": [dict(item) for item in self.store.events.values() if self.store.devices.get(item.get("device_id"), {}).get("user_id") == user_id],
            }
        self._enforce_export_bounds(sections)
        return {"schema": "sentinel.account-export.v1", "generated_at": datetime.now(UTC), "profile": profile, **sections}

    def _export_postgres(self, user_id: str) -> dict[str, Any]:
        with self.store.engine.connect() as conn:
            identity = conn.execute(text(
                "SELECT i.id identity_id,i.user_handle,u.email,u.status,u.created_at "
                "FROM identities i JOIN users u ON u.identity_id=i.id WHERE i.user_handle=:user_id"
            ), {"user_id": user_id}).mappings().first()
            if not identity or identity["status"] != "ACTIVE":
                raise ValueError("ACCOUNT_NOT_FOUND")
            iid = identity["identity_id"]
            profile = {key: identity[key] for key in ("user_handle", "email", "status", "created_at")}
            sections = {
                "devices": self._rows(conn, "SELECT id,platform,state,key_version,created_at,last_seen_at,revoked_at FROM device_bindings WHERE identity_id=:iid ORDER BY created_at", {"iid": iid}),
                "entitlements": self._rows(conn, "SELECT id,game_id,source,status,valid_from,valid_until,created_at FROM entitlements WHERE identity_id=:iid ORDER BY created_at", {"iid": iid}),
                "subscriptions": self._rows(conn, "SELECT id,plan_code,status,currency,provider,provider_subscription_id,started_at,expires_at,updated_at FROM subscriptions WHERE identity_id=:iid ORDER BY started_at", {"iid": iid}),
                "characters": self._rows(conn, "SELECT id,game_id,external_id,name,version,state_json,updated_at FROM characters WHERE identity_id=:iid ORDER BY updated_at", {"iid": iid}),
                "audit": self._rows(conn, "SELECT action,resource,decision,reason_code,policy_version,context,request_id,created_at FROM audit_events WHERE identity_id=:iid ORDER BY created_at", {"iid": iid}),
                "events": self._rows(conn, "SELECT event_id,type,schema_version,occurred_at,sequence,payload_json,request_id,received_at FROM game_events WHERE identity_id=:iid ORDER BY received_at", {"iid": iid}),
                "quality_reports": self._rows(conn, "SELECT id,category,title,description,status,diagnostics_consent,quality_program_opt_in,diagnostics_json,created_at,updated_at FROM quality_reports WHERE user_id=:user_id ORDER BY created_at", {"user_id": user_id}),
            }
        self._enforce_export_bounds(sections)
        return {"schema": "sentinel.account-export.v1", "generated_at": datetime.now(UTC), "profile": profile, **sections}

    def _erase_memory(self, user_id: str, password: str) -> dict[str, Any]:
        tombstone = self._tombstone()
        with self.user_store._lock:
            account = self.user_store._users.get(user_id)
            if not account or account.get("status") != "ACTIVE" or not verify_password(password, account["password_hash"]):
                raise ValueError("ACCOUNT_REAUTH_FAILED")
            self.user_store._users.pop(user_id)
            self.user_store._users[tombstone["email"]] = {
                **account,
                "user_id": tombstone["handle"],
                "email": tombstone["email"],
                "password_hash": hash_password(secrets.token_urlsafe(48)),
                "status": "DISABLED",
                "updated_at": datetime.now(UTC),
            }
        with self.store.lock:
            for session in self.store.sessions.values():
                if session.get("user_id") == user_id:
                    session["revoked"] = True
                    session["user_id"] = tombstone["handle"]
            for device in self.store.devices.values():
                if device.get("user_id") == user_id:
                    device["user_id"] = tombstone["handle"]
                    device["state"] = "REVOKED"
            if user_id in self.store.entitlements:
                items = self.store.entitlements.pop(user_id)
                for item in items:
                    item["user_id"] = tombstone["handle"]
                self.store.entitlements[tombstone["handle"]] = items
            for collection in (self.store.subscriptions, self.store.characters):
                for item in collection.values():
                    if item.get("user_id") == user_id:
                        item["user_id"] = tombstone["handle"]
            for item in self.store.audit:
                if item.get("actor_user_id") == user_id:
                    item["actor_user_id"] = tombstone["handle"]
        return {"status": "ERASED", "tombstone_id": tombstone["public_id"], "sessions_revoked": True, "devices_revoked": True}

    def _erase_postgres(self, user_id: str, password: str) -> dict[str, Any]:
        tombstone = self._tombstone()
        with self.store.engine.begin() as conn:
            account = conn.execute(text(
                "SELECT i.id identity_id,u.password_hash,u.status FROM identities i "
                "JOIN users u ON u.identity_id=i.id WHERE i.user_handle=:user_id FOR UPDATE"
            ), {"user_id": user_id}).mappings().first()
            if not account or account["status"] != "ACTIVE" or not verify_password(password, account["password_hash"]):
                raise ValueError("ACCOUNT_REAUTH_FAILED")
            iid = account["identity_id"]
            conn.execute(text("UPDATE sessions SET revoked_at=COALESCE(revoked_at,now()) WHERE identity_id=:iid"), {"iid": iid})
            conn.execute(text(
                "UPDATE device_bindings SET state='REVOKED', revoked_at=COALESCE(revoked_at,now()) WHERE identity_id=:iid"
            ), {"iid": iid})
            conn.execute(text(
                "UPDATE quality_reports SET user_id=:tombstone,device_id=NULL,title=:title,description=:description,"
                "diagnostics_consent=false,quality_program_opt_in=false,diagnostics_json=NULL,diagnostics_bytes=0,"
                "diagnostics_expires_at=NULL,updated_at=now() WHERE user_id=:user_id"
            ), {"tombstone": tombstone["handle"], "title": _REDACTED_REPORT_TITLE, "description": _REDACTED_REPORT_DESCRIPTION, "user_id": user_id})
            conn.execute(text(
                "UPDATE users SET email=:email,password_hash=:password_hash,status='DISABLED',updated_at=now() WHERE identity_id=:iid"
            ), {"email": tombstone["email"], "password_hash": hash_password(secrets.token_urlsafe(48)), "iid": iid})
            conn.execute(text("UPDATE identities SET user_handle=:handle WHERE id=:iid"), {"handle": tombstone["handle"], "iid": iid})
        return {"status": "ERASED", "tombstone_id": tombstone["public_id"], "sessions_revoked": True, "devices_revoked": True}

    @staticmethod
    def _rows(conn: Any, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        rows = conn.execute(text(sql + " LIMIT :limit"), {**params, "limit": _MAX_EXPORT_ROWS + 1}).mappings().all()
        if len(rows) > _MAX_EXPORT_ROWS:
            raise ValueError("ACCOUNT_EXPORT_TOO_LARGE")
        return [dict(row) for row in rows]

    @staticmethod
    def _safe_device(item: dict[str, Any]) -> dict[str, Any]:
        return {key: item.get(key) for key in ("platform", "state", "key_version", "last_sequence")}

    @staticmethod
    def _enforce_export_bounds(sections: dict[str, list[dict[str, Any]]]) -> None:
        if any(len(items) > _MAX_EXPORT_ROWS for items in sections.values()):
            raise ValueError("ACCOUNT_EXPORT_TOO_LARGE")
        try:
            encoded = json.dumps(sections, default=str, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("ACCOUNT_EXPORT_ENCODING_FAILED") from exc
        if len(encoded) > 16 * 1024 * 1024:
            raise ValueError("ACCOUNT_EXPORT_TOO_LARGE")

    @staticmethod
    def _tombstone() -> dict[str, str]:
        value = uuid.uuid4().hex
        return {
            "public_id": value,
            "handle": f"deleted:{value}",
            "email": f"deleted-{value}@invalid.local",
        }
