from __future__ import annotations

import base64
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Header, HTTPException, Request

from app.core.models import (
    AuthorizeRequest,
    AuthorizeResponse,
    DeviceProofRequest,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    EventBatchRequest,
    Recommendation,
    RecommendationRequest,
    RecommendationResponse,
    SessionResponse,
)
from app.core.security import (
    AuthorizationEngine,
    Decision,
    Policy,
    Principal,
    canonical_json,
    fingerprint_public_key,
    fresh_request_timestamp,
    new_nonce,
    session_hash,
    verify_p256_signature,
)

app = FastAPI(title="SENTINEL CORE", version="0.1.0")


class MemoryStore:
    def __init__(self) -> None:
        self.devices: dict[str, dict] = {}
        self.challenges: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.events: dict[str, dict] = {}
        self.audit: list[dict] = []
        self.entitlements: dict[tuple[str, str], dict] = {}


store = MemoryStore()
policy_engine = AuthorizationEngine(
    [
        Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
        Policy(Decision.ALLOW, "event:write", "game:event", scopes=frozenset({"game:write"})),
        Policy(Decision.ALLOW, "audit:read", "audit", scopes=frozenset({"audit:read"})),
        Policy(Decision.DENY, "*", "*"),
    ]
)


def _request_id(request: Request, header_value: str | None) -> str:
    return header_value or str(uuid.uuid4())


def _audit(user_id: str | None, device_id: str | None, action: str, resource: str, decision: Decision, reason: str) -> None:
    store.audit.append(
        {
            "actor_user_id": user_id,
            "actor_device_id": device_id,
            "action": action,
            "resource": resource,
            "decision": decision.value,
            "reason_code": reason,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )


def _session_principal(token: str) -> Principal:
    record = store.sessions.get(session_hash(token))
    if not record or record["expires_at"] <= time.time() or record.get("revoked"):
        raise HTTPException(status_code=401, detail="INVALID_SESSION")
    return Principal(
        user_id=record["user_id"],
        device_id=record.get("device_id"),
        roles=frozenset(record.get("roles", [])),
        scopes=frozenset(record.get("scopes", [])),
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-core"}


@app.post("/v1/devices/register", response_model=DeviceRegisterResponse)
def register_device(payload: DeviceRegisterRequest, request: Request, x_request_id: str | None = Header(default=None)):
    request_id = _request_id(request, x_request_id)
    expected = fingerprint_public_key(payload.public_key_der_b64)
    if expected != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail={"code": "FINGERPRINT_MISMATCH", "request_id": request_id})
    try:
        device_id = str(uuid.uuid4())
        challenge = new_nonce()
        store.devices[device_id] = {
            "user_id": payload.user_id,
            "platform": payload.platform,
            "public_key": payload.public_key_der_b64,
            "fingerprint": expected,
            "state": "ACTIVE",
            "key_version": 1,
            "last_sequence": -1,
        }
        store.challenges[session_hash(challenge)] = {
            "device_id": device_id,
            "expires_at": time.time() + 120,
            "consumed": False,
        }
        return DeviceRegisterResponse(device_id=device_id, state="ACTIVE", challenge=challenge)
    except Exception as exc:
        _audit(None, None, "device:register", "device", Decision.DENY, type(exc).__name__)
        raise


@app.post("/v1/devices/{device_id}/prove", response_model=SessionResponse)
def prove_device(device_id: str, payload: DeviceProofRequest):
    device = store.devices.get(device_id)
    if not device or device["state"] != "ACTIVE":
        raise HTTPException(status_code=401, detail="DEVICE_NOT_ACTIVE")
    challenge_key = session_hash(payload.challenge)
    challenge = store.challenges.get(challenge_key)
    if not challenge or challenge["device_id"] != device_id or challenge["consumed"] or challenge["expires_at"] < time.time():
        raise HTTPException(status_code=401, detail="INVALID_OR_REPLAYED_CHALLENGE")
    if not fresh_request_timestamp(payload.timestamp):
        raise HTTPException(status_code=401, detail="STALE_REQUEST")
    signed = canonical_json({"challenge": payload.challenge, "timestamp": payload.timestamp, "request_id": payload.request_id})
    if not verify_p256_signature(device["public_key"], payload.signature_b64, signed):
        _audit(device["user_id"], device_id, "device:prove", "session", Decision.DENY, "BAD_SIGNATURE")
        raise HTTPException(status_code=401, detail="BAD_SIGNATURE")
    challenge["consumed"] = True
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(UTC) + timedelta(hours=12)
    store.sessions[session_hash(raw)] = {
        "user_id": device["user_id"],
        "device_id": device_id,
        "scopes": ["character:read", "game:write", "audit:read"],
        "roles": ["user"],
        "expires_at": expires.timestamp(),
    }
    _audit(device["user_id"], device_id, "device:prove", "session", Decision.ALLOW, "PROOF_VALID")
    return SessionResponse(session_token=raw, expires_at=expires, scopes=["character:read", "game:write", "audit:read"])


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


@app.post("/v1/recommendations", response_model=RecommendationResponse)
def recommendations(payload: RecommendationRequest, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = _session_principal(authorization.removeprefix("Bearer "))
    # Deliberately deterministic in the core. An external AI provider may enrich
    # recommendations later, but it cannot change authorization or state.
    recommendations = [
        Recommendation(
            kind="recommendation",
            text="Review the most recent character events before making a progression decision.",
            confidence=0.72,
            provenance=["sentinel-core:context-baseline"],
        )
    ]
    _audit(principal.user_id, principal.device_id, "knowledge:recommend", "recommendation", Decision.ALLOW, "SAFE_RECOMMENDATION")
    return RecommendationResponse(recommendations=recommendations)
