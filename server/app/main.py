from __future__ import annotations

import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.admin import require_admin
from app.core.entitlements import Entitlement, EntitlementStatus
from app.core.game_catalog import DIABLO_CATALOG, get_game
from app.core.models import AuthorizeRequest, AuthorizeResponse, DeviceProofRequest, DeviceRegisterRequest, DeviceRegisterResponse, EventBatchRequest, Recommendation, RecommendationRequest, RecommendationResponse, SessionResponse
from app.core.security import AuthorizationEngine, Decision, Policy, Principal, canonical_json, fingerprint_public_key, fresh_request_timestamp, new_nonce, session_hash, verify_p256_signature

app = FastAPI(title="SENTINEL CORE", version="0.2.0")

class MemoryStore:
    def __init__(self) -> None:
        self.devices: dict[str, dict] = {}
        self.challenges: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.events: dict[str, dict] = {}
        self.audit: list[dict] = []
        self.entitlements: dict[str, list[Entitlement]] = {}

store = MemoryStore()
policy_engine = AuthorizationEngine([
    Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
    Policy(Decision.ALLOW, "event:write", "game:event", scopes=frozenset({"game:write"})),
    Policy(Decision.ALLOW, "audit:read", "audit", scopes=frozenset({"audit:read"})),
    Policy(Decision.ALLOW, "game:read", "game:*", scopes=frozenset({"game:read"})),
])

def _request_id(request: Request, header_value: str | None) -> str:
    return header_value or str(uuid.uuid4())

def _audit(user_id: str | None, device_id: str | None, action: str, resource: str, decision: Decision, reason: str) -> None:
    store.audit.append({"actor_user_id": user_id, "actor_device_id": device_id, "action": action, "resource": resource, "decision": decision.value, "reason_code": reason, "created_at": datetime.now(UTC).isoformat()})

def _session_principal(token: str) -> Principal:
    record = store.sessions.get(session_hash(token))
    if not record or record["expires_at"] <= time.time() or record.get("revoked"):
        raise HTTPException(status_code=401, detail="INVALID_SESSION")
    return Principal(record["user_id"], record.get("device_id"), frozenset(record.get("roles", [])), frozenset(record.get("scopes", [])))

def _require_entitlement(user_id: str, game_id: str) -> None:
    if get_game(game_id) is None:
        raise HTTPException(status_code=404, detail="GAME_NOT_FOUND")
    now = datetime.now(UTC)
    if not any(item.game_id == game_id and item.is_active(now) for item in store.entitlements.get(user_id, [])):
        raise HTTPException(status_code=403, detail="ENTITLEMENT_REQUIRED")

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-core"}

@app.get("/v1/games")
def list_games(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    decision, reason = policy_engine.authorize(principal, "game:read", "game:catalog")
    _audit(principal.user_id, principal.device_id, "game:read", "game:catalog", decision, reason)
    if decision is Decision.DENY:
        raise HTTPException(status_code=403, detail=reason)
    return {"games": [game.__dict__ for game in DIABLO_CATALOG]}

@app.get("/v1/games/{game_id}")
def get_game_details(game_id: str, authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    decision, reason = policy_engine.authorize(principal, "game:read", f"game:{game_id}")
    _audit(principal.user_id, principal.device_id, "game:read", f"game:{game_id}", decision, reason)
    if decision is Decision.DENY:
        raise HTTPException(status_code=403, detail=reason)
    game = get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="GAME_NOT_FOUND")
    return game.__dict__

@app.get("/v1/games/{game_id}/access")
def check_game_access(game_id: str, authorization: str = Header(...)) -> dict[str, object]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    decision, reason = policy_engine.authorize(principal, "game:read", f"game:{game_id}")
    if decision is Decision.DENY:
        _audit(principal.user_id, principal.device_id, "game:access", game_id, decision, reason)
        raise HTTPException(status_code=403, detail=reason)
    _require_entitlement(principal.user_id, game_id)
    _audit(principal.user_id, principal.device_id, "game:access", game_id, Decision.ALLOW, "ENTITLEMENT_VALID")
    return {"game_id": game_id, "decision": "ALLOW", "reason_code": "ENTITLEMENT_VALID"}

@app.post("/v1/devices/register", response_model=DeviceRegisterResponse)
def register_device(payload: DeviceRegisterRequest, request: Request, x_request_id: str | None = Header(default=None)):
    request_id = _request_id(request, x_request_id)
    try:
        expected = fingerprint_public_key(payload.public_key_der_b64)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_PUBLIC_KEY", "request_id": request_id})
    if expected != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail={"code": "FINGERPRINT_MISMATCH", "request_id": request_id})
    device_id, challenge = str(uuid.uuid4()), new_nonce()
    store.devices[device_id] = {"user_id": payload.user_id, "platform": payload.platform, "public_key": payload.public_key_der_b64, "fingerprint": expected, "state": "ACTIVE", "key_version": 1, "last_sequence": -1}
    store.challenges[session_hash(challenge)] = {"device_id": device_id, "expires_at": time.time() + 120, "consumed": False}
    return DeviceRegisterResponse(device_id=device_id, state="ACTIVE", challenge=challenge)

@app.post("/v1/devices/{device_id}/prove", response_model=SessionResponse)
def prove_device(device_id: str, payload: DeviceProofRequest):
    device = store.devices.get(device_id)
    if not device or device["state"] != "ACTIVE":
        raise HTTPException(status_code=401, detail="DEVICE_NOT_ACTIVE")
    challenge = store.challenges.get(session_hash(payload.challenge))
    if not challenge or challenge["device_id"] != device_id or challenge["consumed"] or challenge["expires_at"] < time.time():
        raise HTTPException(status_code=401, detail="INVALID_OR_REPLAYED_CHALLENGE")
    if not fresh_request_timestamp(payload.timestamp):
        raise HTTPException(status_code=401, detail="STALE_REQUEST")
    signed = canonical_json({"challenge": payload.challenge, "timestamp": payload.timestamp, "request_id": payload.request_id})
    if not verify_p256_signature(device["public_key"], payload.signature_b64, signed):
        _audit(device["user_id"], device_id, "device:prove", "session", Decision.DENY, "BAD_SIGNATURE")
        raise HTTPException(status_code=401, detail="BAD_SIGNATURE")
    challenge["consumed"] = True
    raw, expires = secrets.token_urlsafe(48), datetime.now(UTC) + timedelta(hours=12)
    store.sessions[session_hash(raw)] = {"user_id": device["user_id"], "device_id": device_id, "scopes": ["character:read", "game:write", "game:read", "audit:read"], "roles": ["user"], "expires_at": expires.timestamp()}
    _audit(device["user_id"], device_id, "device:prove", "session", Decision.ALLOW, "PROOF_VALID")
    return SessionResponse(session_token=raw, expires_at=expires, scopes=["character:read", "game:write", "game:read", "audit:read"])

@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize(payload: AuthorizeRequest, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    decision, reason = policy_engine.authorize(principal, payload.action, payload.resource)
    _audit(principal.user_id, principal.device_id, payload.action, payload.resource, decision, reason)
    return AuthorizeResponse(decision=decision.value, reason_code=reason)

@app.post("/v1/events:batch")
def ingest_events(payload: EventBatchRequest, authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    decision, reason = policy_engine.authorize(principal, "event:write", "game:event")
    if decision is Decision.DENY:
        _audit(principal.user_id, principal.device_id, "event:write", "game:event", decision, reason)
        raise HTTPException(status_code=403, detail=reason)
    accepted = 0
    for event in payload.events:
        if event.device_id != principal.device_id:
            raise HTTPException(status_code=403, detail="DEVICE_SCOPE_MISMATCH")
        if event.event_id in store.events:
            continue
        device = store.devices.get(event.device_id)
        if not device or event.sequence <= device["last_sequence"]:
            raise HTTPException(status_code=409, detail="SEQUENCE_REPLAY")
        store.events[event.event_id] = event.model_dump(mode="json")
        device["last_sequence"] = event.sequence
        accepted += 1
    _audit(principal.user_id, principal.device_id, "event:write", "game:event", Decision.ALLOW, "EVENTS_ACCEPTED")
    return {"accepted": accepted, "duplicates": len(payload.events) - accepted}

@app.get("/v1/audit")
def audit(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    decision, reason = policy_engine.authorize(principal, "audit:read", "audit")
    if decision is Decision.DENY:
        raise HTTPException(status_code=403, detail=reason)
    return {"events": [item for item in store.audit if item["actor_user_id"] == principal.user_id]}

class AdminEntitlementRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    game_id: str
    source: str = Field(min_length=1, max_length=256)
    valid_from: datetime
    valid_until: datetime

@app.get("/v1/admin/games")
def admin_games(x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_sentinel_admin_token)
    return {"games": [game.__dict__ for game in DIABLO_CATALOG]}

@app.get("/v1/admin/entitlements")
def admin_entitlements(x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_sentinel_admin_token)
    return {"entitlements": [item.__dict__ for values in store.entitlements.values() for item in values]}

@app.post("/v1/admin/entitlements")
def admin_create_entitlement(payload: AdminEntitlementRequest, x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_sentinel_admin_token)
    if get_game(payload.game_id) is None:
        raise HTTPException(status_code=404, detail="GAME_NOT_FOUND")
    if payload.valid_until < payload.valid_from:
        raise HTTPException(status_code=400, detail="INVALID_ENTITLEMENT_WINDOW")
    item = Entitlement(id=str(uuid.uuid4()), user_id=payload.user_id, game_id=payload.game_id, source=payload.source, status=EntitlementStatus.ACTIVE, valid_from=payload.valid_from, valid_until=payload.valid_until)
    store.entitlements.setdefault(payload.user_id, []).append(item)
    _audit(payload.user_id, None, "admin:entitlement:create", payload.game_id, Decision.ALLOW, "ADMIN_GRANT")
    return item.__dict__

@app.post("/v1/recommendations", response_model=RecommendationResponse)
def recommendations(payload: RecommendationRequest, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    result = [Recommendation(kind="recommendation", text="Review the most recent character events before making a progression decision.", confidence=0.72, provenance=["sentinel-core:context-baseline"])]
    _audit(principal.user_id, principal.device_id, "knowledge:recommend", "recommendation", Decision.ALLOW, "SAFE_RECOMMENDATION")
    return RecommendationResponse(recommendations=result)
