from __future__ import annotations

import os
import secrets
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.admin import require_admin
from app.core.integrity import IntegrityNonceStore, IntegrityTier, PlayIntegrityVerifier
from app.core.entitlements import EntitlementStatus
from app.core.game_catalog import DIABLO_CATALOG, get_game
from app.core.models import (
    AdminEntitlementRequest,
    AuthorizeRequest,
    AuthorizeResponse,
    DeviceBindRequest,
    DeviceProofRequest,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    EventBatchRequest,
    LoginRequest,
    Recommendation,
    RecommendationRequest,
    RecommendationResponse,
    RefreshRequest,
    RegisterRequest,
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
    session_hash,
    verify_p256_signature,
)
from app.core.store import MemoryStore, PostgresStore, Store
from app.core.user_store import UserAccountStore
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
user_store = UserAccountStore(DATABASE_URL)
policy_engine = AuthorizationEngine([
    Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
    Policy(Decision.ALLOW, "event:write", "game:event", scopes=frozenset({"game:write"})),
    Policy(Decision.ALLOW, "audit:read", "audit", scopes=frozenset({"audit:read"})),
    Policy(Decision.ALLOW, "game:read", "game:*", scopes=frozenset({"game:read"})),
    Policy(Decision.ALLOW, "knowledge:recommend", "recommendation", scopes=frozenset({"game:read"})),
])


class RateLimiter:
    def __init__(self, limit: int = 120, window: int = 60, max_buckets: int = 10000) -> None:
        if limit <= 0 or window <= 0 or max_buckets <= 0:
            raise ValueError("limit, window, and max_buckets must be positive")
        self.limit, self.window, self.max_buckets = limit, window, max_buckets
        self._hits: dict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            expired_keys = [bucket for bucket, q in self._hits.items() if not q or q[-1] <= cutoff]
            for bucket in expired_keys:
                self._hits.pop(bucket, None)

            q = self._hits.get(key)
            if q is None:
                if len(self._hits) >= self.max_buckets:
                    return False
                q = deque()
                self._hits[key] = q
            else:
                while q and q[0] <= cutoff:
                    q.popleft()
                if not q:
                    self._hits.pop(key, None)
                    q = deque()
                    self._hits[key] = q

            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


rate_limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")), max_buckets=int(os.getenv("RATE_LIMIT_MAX_BUCKETS", "10000")))
integrity_nonces = IntegrityNonceStore()
play_integrity = PlayIntegrityVerifier()


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


def bind_session_to_device(access_token: str, device_id: str) -> None:
    if isinstance(store, MemoryStore):
        record = store.sessions.get(session_hash(access_token))
        if not record or record.get("revoked"):
            raise HTTPException(status_code=401, detail="INVALID_SESSION")
        record["device_id"] = device_id
        return
    with store.engine.begin() as conn:
        result = conn.execute(
            __import__("sqlalchemy").text(
                "UPDATE sessions SET device_id=(SELECT id FROM device_bindings WHERE id=:device_id) WHERE session_hash=:session_hash AND revoked_at IS NULL"
            ),
            {"device_id": device_id, "session_hash": session_hash(access_token)},
        )
        if result.rowcount != 1:
            raise HTTPException(status_code=401, detail="INVALID_SESSION")


def revoke_device_sessions(device_id: str) -> None:
    if isinstance(store, MemoryStore):
        with store.lock:
            for record in store.sessions.values():
                if record.get("device_id") == device_id:
                    record["revoked"] = True
        return
    with store.engine.begin() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                "UPDATE sessions SET revoked_at=now() WHERE device_id=:device_id AND revoked_at IS NULL"
            ),
            {"device_id": device_id},
        )


def set_device_state(device_id: str, state: str) -> None:
    if isinstance(store, MemoryStore):
        device = store.devices.get(device_id)
        if device:
            device["state"] = state
        return
    with store.engine.begin() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                "UPDATE device_bindings SET state=:state, revoked_at=CASE WHEN :state='REVOKED' THEN now() ELSE revoked_at END WHERE id=:device_id"
            ),
            {"device_id": device_id, "state": state},
        )
