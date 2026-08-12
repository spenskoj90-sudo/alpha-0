from __future__ import annotations

import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
    RefreshRequest,
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
    verify_p256_signature,
)
from app.core.store import MemoryStore, PostgresStore, Store

APP_VERSION = "1.0.0-rc1"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
REFRESH_TTL_SECONDS = int(os.getenv("REFRESH_TTL_SECONDS", "2592000"))
MAX_REQUEST_SKEW_SECONDS = int(os.getenv("MAX_REQUEST_SKEW_SECONDS", "120"))
DATABASE_URL = os.getenv("DATABASE_URL")
SENTINEL_ENV = os.getenv("SENTINEL_ENV", "development").lower()
ENROLLMENT_TOKEN = os.getenv("SENTINEL_ENROLLMENT_TOKEN")
REQUIRE_ENROLLMENT = os.getenv("SENTINEL_REQUIRE_ENROLLMENT", "true").lower() == "true"

if SENTINEL_ENV == "production" and not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required in production")
if SENTINEL_ENV == "production" and not ENROLLMENT_TOKEN:
    raise RuntimeError("SENTINEL_ENROLLMENT_TOKEN is required in production")

app = FastAPI(title="SENTINEL CORE", version=APP_VERSION)
store: Store = PostgresStore(DATABASE_URL) if DATABASE_URL else MemoryStore()

policy_engine = AuthorizationEngine([
    Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
    Policy(Decision.ALLOW, "event:write", "game:event", scopes=frozenset({"game:write"})),
    Policy(Decision.ALLOW, "audit:read", "audit", scopes=frozenset({"audit:read"})),
])


class RateLimiter:
    def __init__(self, limit: int = 120, window: int = 60) -> None:
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


rate_limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")))


def request_id(request: Request, supplied: str | None) -> str:
    value = supplied or request.headers.get("X-Request-ID")
    return value if value and len(value) <= 128 else str(uuid.uuid4())


def error_response(code: str, message: str, rid: str, http_status: int) -> JSONResponse:
    return JSONResponse(status_code=http_status, content={"code": code, "message": message, "request_id": rid})


def rate_limit(request: Request, bucket: str) -> None:
    key = f"{bucket}:{request.client.host if request.client else 'unknown'}"
    if not rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="RATE_LIMITED")


def require_enrollment(token: str | None, user_id: str) -> None:
    if not REQUIRE_ENROLLMENT:
        return
    if not ENROLLMENT_TOKEN or not token:
        raise HTTPException(status_code=503, detail="DEVICE_ENROLLMENT_NOT_CONFIGURED")
    try:
        enrolled_user, enrolled_secret = ENROLLMENT_TOKEN.split(":", 1)
    except ValueError:
        raise HTTPException(status_code=503, detail="DEVICE_ENROLLMENT_NOT_CONFIGURED")
    expected = f"{user_id}:{enrolled_secret}"
    if not secrets.compare_digest(enrolled_user, user_id) or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="INVALID_ENROLLMENT_TOKEN")


def principal_from_token(token: str) -> Principal:
    record = store.get_session(token)
    if not record:
        raise HTTPException(status_code=401, detail="INVALID_SESSION")
    return Principal(record["user_id"], record.get("device_id"), frozenset(record.get("roles", [])), frozenset(record.get("scopes", [])))


def authorize(principal: Principal, action: str, resource: str, rid: str) -> None:
    decision, reason = policy_engine.authorize(principal, action, resource)
    store.add_audit({
        "actor_user_id": principal.user_id,
        "actor_device_id": principal.device_id,
        "action": action,
        "resource": resource,
        "decision": decision.value,
        "reason_code": reason,
        "request_id": rid,
    })
    if decision is Decision.DENY:
        raise HTTPException(status_code=403, detail=reason)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return error_response("VALIDATION_ERROR", "Request validation failed", request_id(request, None), 422)


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # Never expose exception messages, SQL details or stack traces to clients.
    return error_response("INTERNAL_ERROR", "Internal server error", request_id(request, None), 500)


@app.middleware("http")
async def response_security_headers(request: Request, call_next):
    rid = request_id(request, None)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if SENTINEL_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-core", "version": APP_VERSION}


@app.post("/v1/devices/register", response_model=DeviceRegisterResponse)
def register_device(
    payload: DeviceRegisterRequest,
    request: Request,
    x_enrollment_token: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
):
    rate_limit(request, "enroll")
    rid = request_id(request, x_request_id)
    require_enrollment(x_enrollment_token, payload.user_id)
    try:
        fingerprint = fingerprint_public_key(payload.public_key_der_b64)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="INVALID_PUBLIC_KEY")
    if fingerprint != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail="FINGERPRINT_MISMATCH")
    challenge = new_nonce()
    device_id = store.register_device(payload.user_id, payload.platform, payload.public_key_der_b64, fingerprint, challenge)
    store.add_audit({"actor_user_id": payload.user_id, "actor_device_id": device_id, "action": "device:register", "resource": "device", "decision": "ALLOW", "reason_code": "DEVICE_REGISTERED", "request_id": rid})
    return DeviceRegisterResponse(device_id=device_id, state="ACTIVE", challenge=challenge)


@app.post("/v1/devices/{device_id}/challenge", response_model=DeviceRegisterResponse)
def issue_challenge(
    device_id: str,
    request: Request,
    x_enrollment_token: str | None = Header(default=None),
):
    rate_limit(request, "challenge")
    device = store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    require_enrollment(x_enrollment_token, device["user_id"])
    if device["state"] != "ACTIVE":
        raise HTTPException(status_code=404, detail="DEVICE_NOT_ACTIVE")
    challenge = store.create_challenge(device_id)
    return DeviceRegisterResponse(device_id=device_id, state="ACTIVE", challenge=challenge)


@app.post("/v1/devices/{device_id}/prove", response_model=SessionResponse)
def prove_device(device_id: str, payload: DeviceProofRequest, request: Request):
    rate_limit(request, "prove")
    device = store.get_device(device_id)
    if not device or device["state"] != "ACTIVE":
        raise HTTPException(status_code=401, detail="DEVICE_NOT_ACTIVE")
    if not fresh_request_timestamp(payload.timestamp, max_skew_seconds=MAX_REQUEST_SKEW_SECONDS):
        raise HTTPException(status_code=401, detail="STALE_REQUEST")
    signed = canonical_json({"challenge": payload.challenge, "timestamp": payload.timestamp, "request_id": payload.request_id})
    if not verify_p256_signature(device["public_key"], payload.signature_b64, signed):
        store.add_audit({"actor_user_id": device["user_id"], "actor_device_id": device_id, "action": "device:prove", "resource": "session", "decision": "DENY", "reason_code": "BAD_SIGNATURE", "request_id": payload.request_id})
        raise HTTPException(status_code=401, detail="BAD_SIGNATURE")
    if not store.consume_challenge(payload.challenge, device_id):
        raise HTTPException(status_code=401, detail="INVALID_OR_REPLAYED_CHALLENGE")
    access, refresh, expires, scopes = store.issue_session(device_id, device["user_id"], SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    store.add_audit({"actor_user_id": device["user_id"], "actor_device_id": device_id, "action": "device:prove", "resource": "session", "decision": "ALLOW", "reason_code": "PROOF_VALID", "request_id": payload.request_id})
    return SessionResponse(session_token=access, refresh_token=refresh, expires_at=expires, scopes=scopes)


@app.post("/v1/sessions/refresh", response_model=SessionResponse)
def refresh_session(payload: RefreshRequest, request: Request, x_request_id: str | None = Header(default=None)):
    rate_limit(request, "refresh")
    rid = request_id(request, x_request_id)
    result = store.rotate_refresh(payload.refresh_token, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    if not result:
        raise HTTPException(status_code=401, detail="INVALID_REFRESH_TOKEN")
    access, refresh, expires, scopes, old = result
    store.add_audit({"actor_user_id": old["user_id"], "actor_device_id": old["device_id"], "action": "session:refresh", "resource": "session", "decision": "ALLOW", "reason_code": "ROTATED", "request_id": rid})
    return SessionResponse(session_token=access, refresh_token=refresh, expires_at=expires, scopes=scopes)


@app.post("/v1/sessions/revoke")
def revoke_session(authorization_header: str = Header(..., alias="Authorization"), x_request_id: str | None = Header(default=None)):
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    token = authorization_header.removeprefix("Bearer ")
    principal = principal_from_token(token)
    if not store.revoke_session(token):
        raise HTTPException(status_code=401, detail="INVALID_SESSION")
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": principal.device_id, "action": "session:revoke", "resource": "session", "decision": "ALLOW", "reason_code": "REVOKED", "request_id": x_request_id})
    return {"revoked": True}


@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize_endpoint(
    payload: AuthorizeRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None),
):
    rid = request_id(request, x_request_id)
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = principal_from_token(authorization_header.removeprefix("Bearer "))
    authorize(principal, payload.action, payload.resource, rid)
    return AuthorizeResponse(decision="ALLOW", reason_code="POLICY_ALLOW")


@app.post("/v1/events:batch")
def ingest_events(
    payload: EventBatchRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    x_request_id: str | None = Header(default=None),
) -> dict[str, int]:
    rid = request_id(request, x_request_id)
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = principal_from_token(authorization_header.removeprefix("Bearer "))
    authorize(principal, "event:write", "game:event", rid)
    events = [event.model_dump(mode="json") for event in payload.events]
    for event in events:
        event["request_id"] = rid
    try:
        result = store.save_event_batch({"user_id": principal.user_id, "device_id": principal.device_id}, events, x_idempotency_key)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=409 if code == "SEQUENCE_REPLAY" else 403, detail=code)
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": principal.device_id, "action": "event:write", "resource": "game:event", "decision": "ALLOW", "reason_code": "EVENTS_ACCEPTED", "request_id": rid})
    return result


@app.get("/v1/audit")
def audit(authorization_header: str = Header(..., alias="Authorization")) -> dict[str, list[dict[str, Any]]]:
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = principal_from_token(authorization_header.removeprefix("Bearer "))
    authorize(principal, "audit:read", "audit", str(uuid.uuid4()))
    return {"events": store.get_audit(principal.user_id)}


@app.post("/v1/recommendations", response_model=RecommendationResponse)
def recommendations(payload: RecommendationRequest, authorization_header: str = Header(..., alias="Authorization")):
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    principal = principal_from_token(authorization_header.removeprefix("Bearer "))
    result = [Recommendation(kind="recommendation", text="Review the most recent character events before making a progression decision.", confidence=0.72, provenance=["sentinel-core:context-baseline"])]
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": principal.device_id, "action": "knowledge:recommend", "resource": "recommendation", "decision": "ALLOW", "reason_code": "SAFE_RECOMMENDATION", "request_id": None})
    return RecommendationResponse(recommendations=result)
