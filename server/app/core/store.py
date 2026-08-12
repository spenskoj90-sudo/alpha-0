from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from sqlalchemy import create_engine, text

from app.core.security import session_hash


class Store(ABC):
    lock: Lock

    @abstractmethod
    def register_device(self, user_id: str, platform: str, public_key_b64: str, fingerprint: str, challenge: str) -> str: ...

    @abstractmethod
    def get_device(self, device_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def create_challenge(self, device_id: str) -> str: ...

    @abstractmethod
    def consume_challenge(self, challenge: str, device_id: str) -> bool: ...

    @abstractmethod
    def issue_session(self, device_id: str, user_id: str, access_ttl: int, refresh_ttl: int) -> tuple[str, str, datetime, list[str]]: ...

    @abstractmethod
    def get_session(self, access_token: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def rotate_refresh(self, refresh_token: str, access_ttl: int, refresh_ttl: int) -> tuple[str, str, datetime, list[str], dict[str, Any]] | None: ...

    @abstractmethod
    def revoke_session(self, access_token: str) -> bool: ...

    @abstractmethod
    def save_event_batch(self, principal: dict[str, Any], events: list[dict[str, Any]], idempotency_key: str | None) -> dict[str, int]: ...

    @abstractmethod
    def add_audit(self, item: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_audit(self, user_id: str) -> list[dict[str, Any]]: ...


class MemoryStore(Store):
    """Deterministic test/dev store. Production requires PostgresStore."""

    def __init__(self) -> None:
        self.devices: dict[str, dict[str, Any]] = {}
        self.challenges: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.events: dict[str, dict[str, Any]] = {}
        self.idempotency: dict[tuple[str, str], dict[str, int]] = {}
        self.audit: list[dict[str, Any]] = []
        self.lock = Lock()

    def register_device(self, user_id, platform, public_key_b64, fingerprint, challenge):
        device_id = str(uuid.uuid4())
        self.devices[device_id] = {
            "user_id": user_id,
            "platform": platform,
            "public_key": public_key_b64,
            "fingerprint": fingerprint,
            "state": "ACTIVE",
            "key_version": 1,
            "last_sequence": -1,
        }
        self.challenges[session_hash(challenge)] = {
            "device_id": device_id,
            "expires_at": time.time() + 120,
            "consumed": False,
        }
        return device_id

    def get_device(self, device_id):
        return self.devices.get(device_id)

    def create_challenge(self, device_id):
        challenge = secrets.token_urlsafe(32)
        self.challenges[session_hash(challenge)] = {
            "device_id": device_id,
            "expires_at": time.time() + 120,
            "consumed": False,
        }
        return challenge

    def consume_challenge(self, challenge, device_id):
        record = self.challenges.get(session_hash(challenge))
        if not record or record["device_id"] != device_id or record["consumed"] or record["expires_at"] < time.time():
            return False
        record["consumed"] = True
        return True

    def issue_session(self, device_id, user_id, access_ttl, refresh_ttl):
        access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(64)
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=access_ttl)
        scopes = ["character:read", "game:write", "audit:read"]
        self.sessions[session_hash(access)] = {
            "user_id": user_id,
            "device_id": device_id,
            "scopes": scopes,
            "roles": ["user"],
            "issued_at": now.timestamp(),
            "expires_at": exp.timestamp(),
            "refresh_hash": session_hash(refresh),
            "refresh_expires_at": (now + timedelta(seconds=refresh_ttl)).timestamp(),
            "refresh_used": False,
            "revoked": False,
        }
        return access, refresh, exp, scopes

    def get_session(self, access_token):
        record = self.sessions.get(session_hash(access_token))
        if not record or record["expires_at"] <= time.time() or record.get("revoked"):
            return None
        return record

    def rotate_refresh(self, refresh_token, access_ttl, refresh_ttl):
        record = next((r for r in self.sessions.values() if r.get("refresh_hash") == session_hash(refresh_token)), None)
        if not record or record.get("revoked") or record["refresh_expires_at"] <= time.time() or record.get("refresh_used"):
            return None
        record["refresh_used"] = True
        access, refresh, exp, scopes = self.issue_session(record["device_id"], record["user_id"], access_ttl, refresh_ttl)
        return access, refresh, exp, scopes, record.copy()

    def revoke_session(self, access_token):
        record = self.sessions.get(session_hash(access_token))
        if not record or record.get("revoked"):
            return False
        record["revoked"] = True
        return True

    def save_event_batch(self, principal, events, idempotency_key):
        key = (principal["user_id"], idempotency_key) if idempotency_key else None
        if key and key in self.idempotency:
            return self.idempotency[key]
        device = self.devices.get(principal["device_id"] or "")
        if not device:
            raise ValueError("DEVICE_NOT_FOUND")
        new_events = [e for e in events if e["event_id"] not in self.events]
        if any(e["device_id"] != principal["device_id"] for e in new_events):
            raise ValueError("DEVICE_SCOPE_MISMATCH")
        if len({e["sequence"] for e in new_events}) != len(new_events) or any(e["sequence"] <= device["last_sequence"] for e in new_events):
            raise ValueError("SEQUENCE_REPLAY")
        for event in sorted(new_events, key=lambda item: item["sequence"]):
            self.events[event["event_id"]] = event
            device["last_sequence"] = event["sequence"]
        result = {"accepted": len(new_events), "duplicates": len(events) - len(new_events)}
        if key:
            self.idempotency[key] = result
        return result

    def add_audit(self, item):
        self.audit.append(item)

    def get_audit(self, user_id):
        return [item for item in self.audit if item["actor_user_id"] == user_id]


class PostgresStore(Store):
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
        self.lock = Lock()

    def register_device(self, user_id, platform, public_key_b64, fingerprint, challenge):
        device_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO users(external_subject) VALUES (:u) ON CONFLICT (external_subject) DO NOTHING"), {"u": user_id})
            conn.execute(text("INSERT INTO devices(id,user_id,state,platform,public_key_der,fingerprint_sha256,key_version) VALUES (:id,(SELECT id FROM users WHERE external_subject=:u),'ACTIVE',:platform,:key,:fp,1)"), {"id": device_id, "u": user_id, "platform": platform, "key": base64.b64decode(public_key_b64, validate=True), "fp": fingerprint})
            conn.execute(text("INSERT INTO device_challenges(device_id,nonce_hash,expires_at) VALUES (:id,:nonce,now()+interval '120 seconds')"), {"id": device_id, "nonce": session_hash(challenge)})
        return device_id

    def get_device(self, device_id):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT d.id::text device_id,u.external_subject user_id,d.platform,d.state,d.public_key_der,d.fingerprint_sha256,d.key_version,COALESCE((SELECT max(sequence) FROM game_events e WHERE e.device_id=d.id),-1) last_sequence FROM devices d JOIN users u ON u.id=d.user_id WHERE d.id=:id"), {"id": device_id}).mappings().first()
        if not row:
            return None
        return {**row, "public_key": base64.b64encode(bytes(row["public_key_der"])).decode(), "last_sequence": int(row["last_sequence"])}

    def create_challenge(self, device_id):
        challenge = secrets.token_urlsafe(32)
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO device_challenges(device_id,nonce_hash,expires_at) VALUES (:id,:nonce,now()+interval '120 seconds')"), {"id": device_id, "nonce": session_hash(challenge)})
        return challenge

    def consume_challenge(self, challenge, device_id):
        with self.engine.begin() as conn:
            result = conn.execute(text("UPDATE device_challenges SET consumed_at=now() WHERE device_id=:id AND nonce_hash=:nonce AND consumed_at IS NULL AND expires_at>now()"), {"id": device_id, "nonce": session_hash(challenge)})
            return result.rowcount == 1

    def issue_session(self, device_id, user_id, access_ttl, refresh_ttl):
        access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(64)
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=access_ttl)
        refexp = now + timedelta(seconds=refresh_ttl)
        scopes = ["character:read", "game:write", "audit:read"]
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO sessions(user_id,device_id,session_hash,scopes_json,issued_at,expires_at,refresh_token_hash,refresh_expires_at) VALUES ((SELECT id FROM users WHERE external_subject=:u),(SELECT id FROM devices WHERE id=:d),:sh,:scopes,now(),:exp,:rh,:rexp)"), {"u": user_id, "d": device_id, "sh": session_hash(access), "scopes": json.dumps(scopes), "exp": exp, "rh": session_hash(refresh), "rexp": refexp})
        return access, refresh, exp, scopes

    def get_session(self, access_token):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT s.user_id::text user_uuid,s.device_id::text device_id,s.scopes_json,s.expires_at,s.revoked_at,u.external_subject FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.session_hash=:sh AND s.expires_at>now() AND s.revoked_at IS NULL"), {"sh": session_hash(access_token)}).mappings().first()
        if not row:
            return None
        scopes = row["scopes_json"] if isinstance(row["scopes_json"], list) else json.loads(row["scopes_json"])
        return {"user_id": row["external_subject"], "device_id": row["device_id"], "scopes": scopes, "roles": ["user"], "expires_at": row["expires_at"].timestamp(), "revoked": False}

    def rotate_refresh(self, refresh_token, access_ttl, refresh_ttl):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT s.id::text session_id,u.external_subject user_id,s.device_id::text device_id,s.scopes_json,s.refresh_expires_at,s.refresh_used_at,s.revoked_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.refresh_token_hash=:rh FOR UPDATE"), {"rh": session_hash(refresh_token)}).mappings().first()
            if not row or row["revoked_at"] or row["refresh_used_at"] or not row["refresh_expires_at"] or row["refresh_expires_at"] <= datetime.now(UTC):
                return None
            conn.execute(text("UPDATE sessions SET refresh_used_at=now(),revoked_at=now() WHERE id=:id"), {"id": row["session_id"]})
        access, refresh, exp, scopes = self.issue_session(row["device_id"], row["user_id"], access_ttl, refresh_ttl)
        return access, refresh, exp, scopes, {"user_id": row["user_id"], "device_id": row["device_id"], "scopes": scopes}

    def revoke_session(self, access_token):
        with self.engine.begin() as conn:
            result = conn.execute(text("UPDATE sessions SET revoked_at=now() WHERE session_hash=:sh AND revoked_at IS NULL"), {"sh": session_hash(access_token)})
            return result.rowcount == 1

    def save_event_batch(self, principal, events, idempotency_key):
        with self.engine.begin() as conn:
            if idempotency_key:
                row = conn.execute(text("SELECT response_json FROM idempotency_keys WHERE key=:k AND actor_id=:a AND expires_at>now()"), {"k": idempotency_key, "a": principal["user_id"]}).mappings().first()
                if row:
                    return row["response_json"]
            new_events = []
            for event in sorted(events, key=lambda item: item["sequence"]):
                if not conn.execute(text("SELECT 1 FROM game_events WHERE event_id=:id"), {"id": event["event_id"]}).first():
                    new_events.append(event)
            if any(event["device_id"] != principal["device_id"] for event in new_events):
                raise ValueError("DEVICE_SCOPE_MISMATCH")
            last = conn.execute(text("SELECT COALESCE(max(sequence),-1) FROM game_events WHERE device_id=(SELECT id FROM devices WHERE id=:d)"), {"d": principal["device_id"]}).scalar_one()
            if len({event["sequence"] for event in new_events}) != len(new_events) or any(event["sequence"] <= last for event in new_events):
                raise ValueError("SEQUENCE_REPLAY")
            device_uuid = conn.execute(text("SELECT id FROM devices WHERE id=:d"), {"d": principal["device_id"]}).scalar_one_or_none()
            user_uuid = conn.execute(text("SELECT id FROM users WHERE external_subject=:u"), {"u": principal["user_id"]}).scalar_one_or_none()
            if not device_uuid or not user_uuid:
                raise ValueError("DEVICE_NOT_FOUND")
            for event in new_events:
                conn.execute(text("INSERT INTO game_events(event_id,device_id,user_id,type,schema_version,occurred_at,sequence,payload_json,request_id) VALUES (:eid,:did,:uid,:type,:sv,:occurred,:seq,:payload,:rid)"), {"eid": event["event_id"], "did": device_uuid, "uid": user_uuid, "type": event["type"], "sv": event["schema_version"], "occurred": event["occurred_at"], "seq": event["sequence"], "payload": json.dumps(event["payload"]), "rid": event.get("request_id")})
            result = {"accepted": len(new_events), "duplicates": len(events) - len(new_events)}
            if idempotency_key:
                conn.execute(text("INSERT INTO idempotency_keys(key,actor_id,request_hash,response_json,expires_at) VALUES (:k,:a,:h,:r,now()+interval '1 day')"), {"k": idempotency_key, "a": principal["user_id"], "h": hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest(), "r": json.dumps(result)})
            return result

    def add_audit(self, item):
        with self.engine.begin() as conn:
            user_id = conn.execute(text("SELECT id FROM users WHERE external_subject=:u"), {"u": item["actor_user_id"]}).scalar_one_or_none() if item["actor_user_id"] else None
            conn.execute(text("INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,decision,reason_code,metadata_json,request_id) VALUES (:u,:action,:rt,:rid,:decision,:reason,:meta,:req)"), {"u": user_id, "action": item["action"], "rt": item["resource"].split(":", 1)[0], "rid": item["resource"], "decision": item["decision"], "reason": item["reason_code"], "meta": json.dumps({}), "req": item.get("request_id")})

    def get_audit(self, user_id):
        with self.engine.begin() as conn:
            rows = conn.execute(text("SELECT action,resource_type,resource_id,decision,reason_code,request_id,created_at FROM audit_events WHERE actor_user_id=(SELECT id FROM users WHERE external_subject=:u) ORDER BY created_at DESC LIMIT 500"), {"u": user_id}).mappings().all()
        return [dict(row) for row in rows]
