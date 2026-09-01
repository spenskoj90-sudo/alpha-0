from __future__ import annotations

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

SCOPES = ["character:read", "game:write", "game:read", "audit:read"]


def event_hash_payload(events: list[dict[str, Any]]) -> str:
    """Hash only durable event intent; request IDs are transport metadata."""
    canonical = [
        {key: value for key, value in event.items() if key != "request_id"}
        for event in events
    ]
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, default=str).encode()).hexdigest()


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
    def consume_proof_request(self, device_id: str, request_id: str) -> bool: ...
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
    @abstractmethod
    def record_security_failure(self, subject: str, source: str) -> int: ...
    @abstractmethod
    def security_failure_count(self, subject: str) -> int: ...
    @abstractmethod
    def list_entitlements(self, user_id: str | None = None) -> list[dict[str, Any]]: ...
    @abstractmethod
    def create_entitlement(self, item: dict[str, Any]) -> dict[str, Any]: ...
    @abstractmethod
    def list_characters(self, user_id: str) -> list[dict[str, Any]]: ...
    @abstractmethod
    def get_character(self, character_id: str) -> dict[str, Any] | None: ...
    @abstractmethod
    def upsert_character(self, item: dict[str, Any]) -> dict[str, Any]: ...


class MemoryStore(Store):
    """Deterministic test/dev store. Production requires PostgresStore."""

    def __init__(self) -> None:
        self.devices: dict[str, dict[str, Any]] = {}
        self.challenges: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.events: dict[str, dict[str, Any]] = {}
        self.idempotency: dict[tuple[str, str], dict[str, Any]] = {}
        self.proof_requests: set[tuple[str, str]] = set()
        self.audit: list[dict[str, Any]] = []
        self.failures: list[tuple[str, float]] = []
        self.entitlements: dict[str, list[dict[str, Any]]] = {}
        self.characters: dict[str, dict[str, Any]] = {}
        self.lock = Lock()

    def register_device(self, user_id, platform, public_key_b64, fingerprint, challenge):
        device_id = str(uuid.uuid4())
        with self.lock:
            self.devices[device_id] = {"user_id": user_id, "platform": platform, "public_key": public_key_b64, "fingerprint": fingerprint, "state": "ACTIVE", "key_version": 1, "last_sequence": -1}
            self.challenges[session_hash(challenge)] = {"device_id": device_id, "expires_at": time.time() + 120, "consumed": False}
        return device_id

    def get_device(self, device_id):
        return self.devices.get(device_id)

    def create_challenge(self, device_id):
        challenge = secrets.token_urlsafe(32)
        with self.lock:
            self.challenges[session_hash(challenge)] = {"device_id": device_id, "expires_at": time.time() + 120, "consumed": False}
        return challenge

    def consume_challenge(self, challenge, device_id):
        with self.lock:
            record = self.challenges.get(session_hash(challenge))
            if not record or record["device_id"] != device_id or record["consumed"] or record["expires_at"] < time.time():
                return False
            record["consumed"] = True
            return True

    def consume_proof_request(self, device_id, request_id):
        with self.lock:
            key = (device_id, request_id)
            if key in self.proof_requests:
                return False
            self.proof_requests.add(key)
            return True

    def issue_session(self, device_id, user_id, access_ttl, refresh_ttl):
        access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(64)
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=access_ttl)
        record = {"user_id": user_id, "device_id": device_id, "scopes": SCOPES, "roles": ["user"], "issued_at": now.timestamp(), "expires_at": exp.timestamp(), "refresh_hash": session_hash(refresh), "refresh_expires_at": (now + timedelta(seconds=refresh_ttl)).timestamp(), "refresh_used": False, "revoked": False}
        with self.lock:
            self.sessions[session_hash(access)] = record
        return access, refresh, exp, SCOPES

    def get_session(self, access_token):
        record = self.sessions.get(session_hash(access_token))
        if not record or record["expires_at"] <= time.time() or record.get("revoked"):
            return None
        return record

    def rotate_refresh(self, refresh_token, access_ttl, refresh_ttl):
        with self.lock:
            record = next((r for r in self.sessions.values() if r.get("refresh_hash") == session_hash(refresh_token)), None)
            if not record or record.get("revoked") or record["refresh_expires_at"] <= time.time() or record.get("refresh_used"):
                return None
            record["refresh_used"] = True
            record["revoked"] = True
            old = record.copy()
            access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(64)
            now = datetime.now(UTC)
            exp = now + timedelta(seconds=access_ttl)
            new_record = {
                "user_id": old["user_id"],
                "device_id": old["device_id"],
                "scopes": SCOPES,
                "roles": ["user"],
                "issued_at": now.timestamp(),
                "expires_at": exp.timestamp(),
                "refresh_hash": session_hash(refresh),
                "refresh_expires_at": (now + timedelta(seconds=refresh_ttl)).timestamp(),
                "refresh_used": False,
                "revoked": False,
            }
            self.sessions[session_hash(access)] = new_record
        return access, refresh, exp, SCOPES, old

    def revoke_session(self, access_token):
        with self.lock:
            record = self.sessions.get(session_hash(access_token))
            if not record or record.get("revoked"):
                return False
            record["revoked"] = True
            return True

    def save_event_batch(self, principal, events, idempotency_key):
        request_hash = event_hash_payload(events)
        with self.lock:
            key = (principal["user_id"], idempotency_key) if idempotency_key else None
            if key and key in self.idempotency:
                cached = self.idempotency[key]
                if cached["request_hash"] != request_hash:
                    raise ValueError("IDEMPOTENCY_KEY_REUSE")
                return cached["response"]
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
                self.idempotency[key] = {"request_hash": request_hash, "response": result}
            return result

    def add_audit(self, item):
        self.audit.append(item)

    def get_audit(self, user_id):
        return [item for item in self.audit if item.get("actor_user_id") == user_id]

    def record_security_failure(self, subject, source):
        cutoff = time.time() - 900
        with self.lock:
            self.failures = [(s, t) for s, t in self.failures if t >= cutoff]
            self.failures.append((subject, time.time()))
            return sum(1 for s, _ in self.failures if s == subject)

    def security_failure_count(self, subject):
        cutoff = time.time() - 900
        with self.lock:
            self.failures = [(s, t) for s, t in self.failures if t >= cutoff]
            return sum(1 for s, _ in self.failures if s == subject)

    def list_entitlements(self, user_id=None):
        values = [item for items in self.entitlements.values() for item in items]
        return [item for item in values if user_id is None or item["user_id"] == user_id]

    def create_entitlement(self, item):
        with self.lock:
            self.entitlements.setdefault(item["user_id"], []).append(item)
        return item

    def list_characters(self, user_id: str) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(item) for item in self.characters.values() if item["user_id"] == user_id]

    def get_character(self, character_id: str) -> dict[str, Any] | None:
        with self.lock:
            item = self.characters.get(character_id)
            return dict(item) if item else None

    def upsert_character(self, item: dict[str, Any]) -> dict[str, Any]:
        character_id = item.get("id") or str(uuid.uuid4())
        record = {
            "id": character_id,
            "user_id": item["user_id"],
            "game_id": item["game_id"],
            "external_id": item["external_id"],
            "name": item["name"],
            "version": int(item.get("version", 0)),
            "state_json": item.get("state_json") if isinstance(item.get("state_json"), dict) else {},
            "updated_at": item.get("updated_at") or datetime.now(UTC).isoformat(),
        }
        with self.lock:
            # unique (user_id, game_id, external_id)
            for existing_id, existing in list(self.characters.items()):
                if (
                    existing["user_id"] == record["user_id"]
                    and existing["game_id"] == record["game_id"]
                    and existing["external_id"] == record["external_id"]
                    and existing_id != character_id
                ):
                    del self.characters[existing_id]
                    record["id"] = existing_id
                    character_id = existing_id
                    break
            self.characters[character_id] = record
        return dict(record)


class PostgresStore(Store):
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"options": "-c app.service_role=true"},
        )
        self.lock = Lock()

    def register_device(self, user_id, platform, public_key_b64, fingerprint, challenge):
        device_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            identity = conn.execute(text("INSERT INTO identities(user_handle) VALUES (:u) ON CONFLICT (user_handle) DO UPDATE SET user_handle=EXCLUDED.user_handle RETURNING id"), {"u": user_id}).scalar_one()
            conn.execute(text("INSERT INTO device_bindings(id,identity_id,state,platform,public_key_der_b64,fingerprint_sha256,key_version) VALUES (:id,:uid,'ACTIVE',:platform,:key,:fp,1)"), {"id": device_id, "uid": identity, "platform": platform, "key": public_key_b64, "fp": fingerprint})
            conn.execute(text("INSERT INTO device_challenges(device_id,nonce_hash,expires_at) VALUES (:id,:nonce,now()+interval '120 seconds')"), {"id": device_id, "nonce": session_hash(challenge)})
        return device_id

    def get_device(self, device_id):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT d.id::text device_id,i.user_handle user_id,d.platform,d.state,d.public_key_der_b64 public_key,d.fingerprint_sha256 fingerprint,d.key_version,COALESCE((SELECT max(sequence) FROM game_events e WHERE e.device_id=d.id),-1) last_sequence FROM device_bindings d JOIN identities i ON i.id=d.identity_id WHERE d.id=:id"), {"id": device_id}).mappings().first()
        return dict(row) if row else None

    def create_challenge(self, device_id):
        challenge = secrets.token_urlsafe(32)
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO device_challenges(device_id,nonce_hash,expires_at) VALUES (:id,:nonce,now()+interval '120 seconds')"), {"id": device_id, "nonce": session_hash(challenge)})
        return challenge

    def consume_challenge(self, challenge, device_id):
        with self.engine.begin() as conn:
            result = conn.execute(text("UPDATE device_challenges SET consumed_at=now() WHERE device_id=:id AND nonce_hash=:nonce AND consumed_at IS NULL AND expires_at>now()"), {"id": device_id, "nonce": session_hash(challenge)})
            return result.rowcount == 1

    def consume_proof_request(self, device_id, request_id):
        with self.engine.begin() as conn:
            result = conn.execute(text("INSERT INTO proof_request_ids(device_id,request_id) VALUES (:d,:r) ON CONFLICT DO NOTHING"), {"d": device_id, "r": request_id})
            return result.rowcount == 1

    def issue_session(self, device_id, user_id, access_ttl, refresh_ttl):
        access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(64)
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=access_ttl)
        refexp = now + timedelta(seconds=refresh_ttl)
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO sessions(identity_id,device_id,session_hash,scopes_json,issued_at,expires_at,refresh_token_hash,refresh_expires_at) VALUES ((SELECT id FROM identities WHERE user_handle=:u),(SELECT id FROM device_bindings WHERE id=:d),:sh,:scopes,now(),:exp,:rh,:rexp)"), {"u": user_id, "d": device_id, "sh": session_hash(access), "scopes": json.dumps(SCOPES), "exp": exp, "rh": session_hash(refresh), "rexp": refexp})
        return access, refresh, exp, SCOPES

    def get_session(self, access_token):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT s.identity_id::text identity_id,s.device_id::text device_id,s.scopes_json,s.expires_at,i.user_handle FROM sessions s JOIN identities i ON i.id=s.identity_id WHERE s.session_hash=:sh AND s.expires_at>now() AND s.revoked_at IS NULL"), {"sh": session_hash(access_token)}).mappings().first()
        if not row:
            return None
        scopes = row["scopes_json"] if isinstance(row["scopes_json"], list) else json.loads(row["scopes_json"])
        return {"user_id": row["user_handle"], "device_id": row["device_id"], "scopes": scopes, "roles": ["user"], "expires_at": row["expires_at"].timestamp(), "revoked": False}

    def rotate_refresh(self, refresh_token, access_ttl, refresh_ttl):
        """Atomic rotation: lock, validate, revoke, insert replacement — single transaction."""
        access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(64)
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=access_ttl)
        refexp = now + timedelta(seconds=refresh_ttl)
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT s.id::text session_id,i.user_handle user_id,s.device_id::text device_id,"
                    "s.refresh_expires_at,s.refresh_used_at,s.revoked_at,i.id identity_id "
                    "FROM sessions s JOIN identities i ON i.id=s.identity_id "
                    "WHERE s.refresh_token_hash=:rh FOR UPDATE"
                ),
                {"rh": session_hash(refresh_token)},
            ).mappings().first()
            if not row or row["revoked_at"] or row["refresh_used_at"] or not row["refresh_expires_at"] or row["refresh_expires_at"] <= datetime.now(UTC):
                return None
            conn.execute(
                text("UPDATE sessions SET refresh_used_at=now(),revoked_at=now() WHERE id=:id"),
                {"id": row["session_id"]},
            )
            device_id = row["device_id"]
            conn.execute(
                text(
                    "INSERT INTO sessions(identity_id,device_id,session_hash,scopes_json,issued_at,expires_at,"
                    "refresh_token_hash,refresh_expires_at) VALUES ("
                    ":identity_id,"
                    "CAST(:device_id AS uuid),"
                    ":sh,:scopes,now(),:exp,:rh,:rexp)"
                ),
                {
                    "identity_id": row["identity_id"],
                    "device_id": device_id,
                    "sh": session_hash(access),
                    "scopes": json.dumps(SCOPES),
                    "exp": exp,
                    "rh": session_hash(refresh),
                    "rexp": refexp,
                },
            )
        return access, refresh, exp, SCOPES, {"user_id": row["user_id"], "device_id": row["device_id"], "scopes": SCOPES}

    def revoke_session(self, access_token):
        with self.engine.begin() as conn:
            result = conn.execute(text("UPDATE sessions SET revoked_at=now() WHERE session_hash=:sh AND revoked_at IS NULL"), {"sh": session_hash(access_token)})
            return result.rowcount == 1

    def save_event_batch(self, principal, events, idempotency_key):
        request_hash = event_hash_payload(events)
        with self.engine.begin() as conn:
            if idempotency_key:
                row = conn.execute(text("SELECT request_hash,response_json FROM idempotency_keys WHERE key=:k AND actor_id=:a AND expires_at>now() FOR UPDATE"), {"k": idempotency_key, "a": principal["user_id"]}).mappings().first()
                if row:
                    if row["request_hash"] != request_hash:
                        raise ValueError("IDEMPOTENCY_KEY_REUSE")
                    return row["response_json"]
            device_uuid = conn.execute(text("SELECT id FROM device_bindings WHERE id=:d FOR UPDATE"), {"d": principal["device_id"]}).scalar_one_or_none()
            user_uuid = conn.execute(text("SELECT id FROM identities WHERE user_handle=:u"), {"u": principal["user_id"]}).scalar_one_or_none()
            if not device_uuid or not user_uuid:
                raise ValueError("DEVICE_NOT_FOUND")
            new_events = []
            for event in sorted(events, key=lambda item: item["sequence"]):
                if not conn.execute(text("SELECT 1 FROM game_events WHERE event_id=:id"), {"id": event["event_id"]}).first():
                    new_events.append(event)
            if any(event["device_id"] != principal["device_id"] for event in new_events):
                raise ValueError("DEVICE_SCOPE_MISMATCH")
            last = conn.execute(text("SELECT COALESCE(max(sequence),-1) FROM game_events WHERE device_id=:d"), {"d": device_uuid}).scalar_one()
            if len({event["sequence"] for event in new_events}) != len(new_events) or any(event["sequence"] <= last for event in new_events):
                raise ValueError("SEQUENCE_REPLAY")
            for event in new_events:
                conn.execute(text("INSERT INTO game_events(event_id,device_id,identity_id,type,schema_version,occurred_at,sequence,payload_json,request_id) VALUES (:eid,:did,:uid,:type,:sv,:occurred,:seq,:payload,:rid)"), {"eid": event["event_id"], "did": device_uuid, "uid": user_uuid, "type": event["type"], "sv": event["schema_version"], "occurred": event["occurred_at"], "seq": event["sequence"], "payload": json.dumps(event["payload"]), "rid": event.get("request_id")})
            result = {"accepted": len(new_events), "duplicates": len(events) - len(new_events)}
            if idempotency_key:
                conn.execute(text("INSERT INTO idempotency_keys(key,actor_id,request_hash,response_json,expires_at) VALUES (:k,:a,:h,:r,now()+interval '1 day')"), {"k": idempotency_key, "a": principal["user_id"], "h": request_hash, "r": json.dumps(result)})
            return result

    def add_audit(self, item):
        with self.engine.begin() as conn:
            identity_id = conn.execute(text("SELECT id FROM identities WHERE user_handle=:u"), {"u": item.get("actor_user_id")}).scalar_one_or_none() if item.get("actor_user_id") else None
            conn.execute(text("INSERT INTO audit_events(identity_id,device_id,action,resource,decision,reason_code,context,request_id) VALUES (:u,:d,:action,:resource,:decision,:reason,:context,:req)"), {"u": identity_id, "d": item.get("actor_device_id"), "action": item["action"], "resource": item["resource"], "decision": item["decision"], "reason": item["reason_code"], "context": json.dumps(item.get("metadata", {})), "req": item.get("request_id")})

    def get_audit(self, user_id):
        with self.engine.begin() as conn:
            rows = conn.execute(text("SELECT action,resource,decision,reason_code,request_id,created_at FROM audit_events WHERE identity_id=(SELECT id FROM identities WHERE user_handle=:u) ORDER BY created_at DESC LIMIT 500"), {"u": user_id}).mappings().all()
        return [dict(row) for row in rows]

    def record_security_failure(self, subject, source):
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO security_failures(subject,source) VALUES (:s,:src)"), {"s": subject, "src": source})
            return int(conn.execute(text("SELECT count(*) FROM security_failures WHERE subject=:s AND failed_at>now()-interval '15 minutes'"), {"s": subject}).scalar_one())

    def security_failure_count(self, subject):
        with self.engine.begin() as conn:
            return int(conn.execute(text("SELECT count(*) FROM security_failures WHERE subject=:s AND failed_at>now()-interval '15 minutes'"), {"s": subject}).scalar_one())

    def list_entitlements(self, user_id=None):
        with self.engine.begin() as conn:
            rows = conn.execute(text("SELECT e.id::text id,i.user_handle user_id,e.game_id,e.source,e.status,e.valid_from,e.valid_until FROM entitlements e JOIN identities i ON i.id=e.identity_id WHERE (:u IS NULL OR i.user_handle=:u) ORDER BY e.valid_until DESC"), {"u": user_id}).mappings().all()
        return [dict(row) for row in rows]

    def create_entitlement(self, item):
        with self.engine.begin() as conn:
            identity_id = conn.execute(text("SELECT id FROM identities WHERE user_handle=:u"), {"u": item["user_id"]}).scalar_one_or_none()
            if not identity_id:
                identity_id = conn.execute(text("INSERT INTO identities(user_handle) VALUES (:u) RETURNING id"), {"u": item["user_id"]}).scalar_one()
            conn.execute(text("INSERT INTO entitlements(id,identity_id,game_id,source,status,valid_from,valid_until) VALUES (:id,:uid,:gid,:source,:status,:vf,:vu)"), {"id": item["id"], "uid": identity_id, "gid": item["game_id"], "source": item["source"], "status": item["status"], "vf": item["valid_from"], "vu": item["valid_until"]})
        return item

    def list_characters(self, user_id: str) -> list[dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT c.id::text id, i.user_handle user_id, c.game_id, c.external_id, c.name, "
                    "c.version, c.state_json, c.updated_at "
                    "FROM characters c JOIN identities i ON i.id=c.identity_id "
                    "WHERE i.user_handle=:u ORDER BY c.updated_at DESC"
                ),
                {"u": user_id},
            ).mappings().all()
        result = []
        for row in rows:
            item = dict(row)
            state = item.get("state_json")
            if isinstance(state, str):
                item["state_json"] = json.loads(state)
            if item.get("updated_at") is not None:
                item["updated_at"] = item["updated_at"].isoformat()
            result.append(item)
        return result

    def get_character(self, character_id: str) -> dict[str, Any] | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT c.id::text id, i.user_handle user_id, c.game_id, c.external_id, c.name, "
                    "c.version, c.state_json, c.updated_at "
                    "FROM characters c JOIN identities i ON i.id=c.identity_id "
                    "WHERE c.id=:id"
                ),
                {"id": character_id},
            ).mappings().first()
        if not row:
            return None
        item = dict(row)
        state = item.get("state_json")
        if isinstance(state, str):
            item["state_json"] = json.loads(state)
        if item.get("updated_at") is not None:
            item["updated_at"] = item["updated_at"].isoformat()
        return item

    def upsert_character(self, item: dict[str, Any]) -> dict[str, Any]:
        character_id = item.get("id") or str(uuid.uuid4())
        state_json = item.get("state_json") if isinstance(item.get("state_json"), dict) else {}
        version = int(item.get("version", 0))
        with self.engine.begin() as conn:
            identity_id = conn.execute(text("SELECT id FROM identities WHERE user_handle=:u"), {"u": item["user_id"]}).scalar_one_or_none()
            if not identity_id:
                identity_id = conn.execute(text("INSERT INTO identities(user_handle) VALUES (:u) RETURNING id"), {"u": item["user_id"]}).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO characters(id, identity_id, game_id, external_id, name, version, state_json, updated_at) "
                    "VALUES (:id, :uid, :gid, :ext, :name, :ver, CAST(:state AS jsonb), now()) "
                    "ON CONFLICT (identity_id, game_id, external_id) DO UPDATE SET "
                    "name=EXCLUDED.name, version=EXCLUDED.version, state_json=EXCLUDED.state_json, updated_at=now() "
                    "RETURNING id::text"
                ),
                {
                    "id": character_id,
                    "uid": identity_id,
                    "gid": item["game_id"],
                    "ext": item["external_id"],
                    "name": item["name"],
                    "ver": version,
                    "state": json.dumps(state_json),
                },
            )
        loaded = self.get_character(character_id)
        if loaded:
            return loaded
        # Conflict path may have kept prior UUID — resolve by natural key
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT c.id::text FROM characters c JOIN identities i ON i.id=c.identity_id "
                    "WHERE i.user_handle=:u AND c.game_id=:g AND c.external_id=:e"
                ),
                {"u": item["user_id"], "g": item["game_id"], "e": item["external_id"]},
            ).scalar_one()
        return self.get_character(row) or {
            "id": row,
            "user_id": item["user_id"],
            "game_id": item["game_id"],
            "external_id": item["external_id"],
            "name": item["name"],
            "version": version,
            "state_json": state_json,
        }
