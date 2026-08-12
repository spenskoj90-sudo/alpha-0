from __future__ import annotations

import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.admin import require_admin
from app.core.entitlements import EntitlementStatus
from app.core.game_catalog import DIABLO_CATALOG, get_game
from app.core.models import (
    AdminEntitlementRequest,
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
    verify_p256_signature,
)
from app.core.store import MemoryStore, PostgresStore, Store
from app.core.wow_api import router as wow_router

APP_VERSION = "1.0.0-rc1"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
REFRESH_TTL_SECONDS = int(os.getenv("REFRESH_TTL_SECONDS", "2592000"))
MAX_REQUEST_SKEW_SECONDS = int(os.getenv("MAX_REQUEST_SKEW_SECONDS", "120"))
DATABASE_URL = os.getenv("DATABASE_URL")
SENTINEL_ENV = os.getenv("SENTINEL_ENV", "development").lower()
ENROLLMENT_TOKEN = os.getenv("SENTINEL_ENROLLMENT_TOKEN")
REQUIRE_ENROLLMENT = os.getenv("SENTINEL_REQUIRE_ENROLLMENT", "true").lower() == "true"
CORS_ORIGINS = [item.strip() for item in os.getenv("CORS_ORIGINS", "").split(",") if item.strip()]

if SENTINEL_ENV == "production" and not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required in production")
if SENTINEL_ENV == "production" and not ENROLLMENT_TOKEN:
    raise RuntimeError("SENTINEL_ENROLLMENT_TOKEN is required in production")

app = FastAPI(title="SENTINEL CORE", version=APP_VERSION)
app.include_router(wow_router)
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Enrollment-Token", "Idempotency-Key", "X-Sentinel-Admin-Token"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response


store: Store = PostgresStore(DATABASE_URL) if DATABASE_URL else MemoryStore()
policy_engine = AuthorizationEngine([
    Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
    Policy(Decision.ALLOW, "event:write", "game:event", scopes=frozenset({"game:write"})),
    Policy(Decision.ALLOW, "audit:read", "audit", scopes=frozenset({"audit:read"})),
    Policy(Decision.ALLOW, "game:read", "game:*", scopes=frozenset({"game:read"})),
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


def request_id(request: Request, supplied: str | None = None) -> str:
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
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="DEVICE_ENROLLMENT_NOT_CONFIGURED") from exc
    expected = f"{user_id}:{enrolled_secret}"
    if not secrets.compare_digest(enrolled_user, user_id) or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="INVALID_ENROLLMENT_TOKEN")


def principal_from_token(token: str) -> Principal:
    record = store.get_session(token)
    if not record:
        raise HTTPException(status_code=401, detail="INVALID_SESSION")
    return Principal(record["user_id"], record.get("device_id"), frozenset(record.get("roles", [])), frozenset(record.get("scopes", [])))


def require_bearer(authorization_header: str) -> str:
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    token = authorization_header[7:].strip()
    if not token or len(token) > 4096:
        raise HTTPException(status_code=401, detail="INVALID_AUTHORIZATION")
    return token


def authorize_request(principal: Principal, action: str, resource: str, rid: str) -> None:
    decision, reason = policy_engine.authorize(principal, action, resource)
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": principal.device_id, "action": action, "resource": resource, "decision": decision.value, "reason_code": reason, "request_id": rid})
    if decision is Decision.DENY:
        raise HTTPException(status_code=403, detail=reason)


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response("VALIDATION_ERROR", "Invalid request", request_id(request), 422)


@app.exception_handler(HTTPException)
def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    rid = request_id(request)
    code = str(exc.detail)
    return error_response(code, "Request rejected", rid, exc.status_code)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    if isinstance(store, PostgresStore):
        try:
            with store.engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="DATABASE_UNAVAILABLE") from exc
    return {"status": "UP", "version": APP_VERSION}


@app.post("/v1/devices/register", response_model=DeviceRegisterResponse)
def register_device(
    payload: DeviceRegisterRequest,
    request: Request,
    x_enrollment_token: str | None = Header(default=None, alias="X-Enrollment-Token"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    rid = request_id(request, x_request_id)
    rate_limit(request, "device-register")
    require_enrollment(x_enrollment_token, payload.user_id)
    try:
        fingerprint = fingerprint_public_key(payload.public_key_der_b64)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="INVALID_PUBLIC_KEY") from exc
    if fingerprint.lower() != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail="FINGERPRINT_MISMATCH")
    challenge = __import__("secrets").token_urlsafe(32)
    device_id = store.register_device(payload.user_id, payload.platform, payload.public_key_der_b64, fingerprint, challenge)
    return DeviceRegisterResponse(device_id=device_id, state="ACTIVE", challenge=challenge)


@app.post("/v1/devices/{device_id}/prove", response_model=SessionResponse)
def prove_device(device_id: str, payload: DeviceProofRequest, request: Request):
    rid = request_id(request, payload.request_id)
    device = store.get_device(device_id)
    if not device or device["state"] != "ACTIVE":
        raise HTTPException(status_code=401, detail="DEVICE_NOT_ACTIVE")
    if not fresh_request_timestamp(payload.timestamp, int(time.time()), MAX_REQUEST_SKEW_SECONDS):
        raise HTTPException(status_code=401, detail="STALE_REQUEST")
    if not store.consume_challenge(payload.challenge, device_id):
        raise HTTPException(status_code=401, detail="INVALID_OR_REPLAYED_CHALLENGE")
    proof_payload = canonical_json({"challenge": payload.challenge, "timestamp": payload.timestamp, "request_id": rid})
    if not verify_p256_signature(device["public_key"], payload.signature_b64, proof_payload):
        store.add_audit({"actor_user_id": device["user_id"], "actor_device_id": device_id, "action": "device:prove", "resource": "session", "decision": "DENY", "reason_code": "BAD_SIGNATURE", "request_id": rid})
        raise HTTPException(status_code=401, detail="BAD_SIGNATURE")
    if not store.consume_proof_request(device_id, rid):
        raise HTTPException(status_code=409, detail="REPLAY_DETECTED")
    access, refresh, expires_at, scopes = store.issue_session(device_id, device["user_id"], SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    store.add_audit({"actor_user_id": device["user_id"], "actor_device_id": device_id, "action": "device:prove", "resource": "session", "decision": "ALLOW", "reason_code": "PROOF_VALID", "request_id": rid})
    return SessionResponse(session_token=access, refresh_token=refresh, expires_at=expires_at, scopes=scopes)


@app.post("/v1/sessions/refresh", response_model=SessionResponse)
def refresh_session(payload: RefreshRequest):
    result = store.rotate_refresh(payload.refresh_token, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    if not result:
        raise HTTPException(status_code=401, detail="INVALID_REFRESH")
    access, refresh, expires_at, scopes, _ = result
    return SessionResponse(session_token=access, refresh_token=refresh, expires_at=expires_at, scopes=scopes)


@app.post("/v1/sessions/revoke")
def revoke_session(authorization_header: str = Header(..., alias="Authorization")):
    token = require_bearer(authorization_header)
    principal = principal_from_token(token)
    if not store.revoke_session(token):
        raise HTTPException(status_code=401, detail="INVALID_SESSION")
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": principal.device_id, "action": "session:revoke", "resource": "session", "decision": "ALLOW", "reason_code": "REVOKED", "request_id": None})
    return {"revoked": True}


@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize_endpoint(
    payload: AuthorizeRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    decision, reason = policy_engine.authorize(principal, payload.action, payload.resource)
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": principal.device_id, "action": payload.action, "resource": payload.resource, "decision": decision.value, "reason_code": reason, "request_id": rid})
    return AuthorizeResponse(decision=decision.value, reason_code=reason)


@app.post("/v1/events:batch")
def ingest_events(
    payload: EventBatchRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, int]:
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "event:write", "game:event", rid)
    events = [event.model_dump(mode="json") for event in payload.events]
    for event in events:
        event["request_id"] = rid
    try:
        return store.save_event_batch({"user_id": principal.user_id, "device_id": principal.device_id}, events, x_idempotency_key)
    except ValueError as exc:
        code = str(exc)
        status = 409 if code in {"SEQUENCE_REPLAY", "IDEMPOTENCY_KEY_REUSE"} else 403
        raise HTTPException(status_code=status, detail=code) from exc


@app.get("/v1/audit")
def audit(authorization_header: str = Header(..., alias="Authorization")):
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "audit:read", "audit", str(uuid.uuid4()))
    return {"events": store.get_audit(principal.user_id)}


@app.get("/v1/admin/games")
def admin_games(x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_sentinel_admin_token)
    return {"games": [game.__dict__ for game in DIABLO_CATALOG]}


@app.get("/v1/admin/entitlements")
def admin_entitlements(x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_sentinel_admin_token)
    return {"entitlements": store.list_entitlements()}


@app.post("/v1/admin/entitlements")
def admin_create_entitlement(payload: AdminEntitlementRequest, x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_sentinel_admin_token)
    if get_game(payload.game_id) is None:
        raise HTTPException(status_code=404, detail="GAME_NOT_FOUND")
    if payload.valid_until < payload.valid_from:
        raise HTTPException(status_code=400, detail="INVALID_ENTITLEMENT_WINDOW")
    item = {"id": str(uuid.uuid4()), "user_id": payload.user_id, "game_id": payload.game_id, "source": payload.source, "status": EntitlementStatus.ACTIVE, "valid_from": payload.valid_from, "valid_until": payload.valid_until}
    store.create_entitlement(item)
    store.add_audit({"actor_user_id": payload.user_id, "actor_device_id": None, "action": "admin:entitlement:create", "resource": payload.game_id, "decision": "ALLOW", "reason_code": "ADMIN_GRANT", "request_id": None})
    return item


@app.post("/v1/recommendations", response_model=RecommendationResponse)
def recommendations(payload: RecommendationRequest, authorization_header: str = Header(..., alias="Authorization")):
    principal = principal_from_token(require_bearer(authorization_header))
    result = [Recommendation(kind="recommendation", text="Review the most recent character events before making a progression decision.", confidence=0.72, provenance=["sentinel-core:context-baseline"])]
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": principal.device_id, "action": "knowledge:recommend", "resource": "recommendation", "decision": "ALLOW", "reason_code": "SAFE_RECOMMENDATION", "request_id": None})
    return RecommendationResponse(recommendations=result)
