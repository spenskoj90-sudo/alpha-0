from __future__ import annotations

import os
import secrets
import time
import uuid
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.account_notifications import send_password_reset_email, send_verification_email
from app.core.admin import require_admin
from app.core.billing import BillingService, BillingWebhookEvent
from app.core.p1_runtime import BillingState
from app.core.character_projection import apply_character_projections
from app.core.integrity import IntegrityNonceStore, IntegrityTier, PlayIntegrityVerifier
from app.core.email_provider import configured_email_transport
from app.core.entitlements import EntitlementStatus
from app.core.federated_auth import (
    FederatedAuthError,
    VerifiedFederatedIdentity,
    complete_telegram,
    complete_vk,
    provider_status,
    provider_statuses,
    start_browser_flow,
    verify_google_id_token,
)
from app.core.game_catalog import DIABLO_CATALOG, get_game
from app.core.game_state_routes import install_game_state_routes
from app.core.models import (
    AccountSecurityResponse,
    AdminEntitlementRequest,
    AuthActionResponse,
    AuthTokenRequest,
    AuthorizeRequest,
    AuthorizeResponse,
    DeviceBindRequest,
    DeviceProofRequest,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    EmailActionRequest,
    BrowserAuthCompleteRequest,
    BrowserAuthStartRequest,
    BrowserAuthStartResponse,
    FederatedProviderStatusResponse,
    FederatedProvidersResponse,
    GoogleAuthChallengeResponse,
    GoogleCredentialRequest,
    EventBatchRequest,
    LoginRequest,
    Recommendation,
    RecommendationRequest,
    RecommendationResponse,
    PasswordResetConfirmRequest,
    RefreshRequest,
    RegisterRequest,
    SessionResponse,
    BillingSubscriptionRequest,
    BillingWebhookRequest,
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

APP_VERSION = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
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
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Enrollment-Token", "Idempotency-Key", "X-Sentinel-Admin-Token", "X-Sentinel-Admin-TOTP"],
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
email_transport = configured_email_transport()
policy_engine = AuthorizationEngine([
    Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})),
    Policy(Decision.ALLOW, "event:write", "game:event", scopes=frozenset({"game:write"})),
    Policy(Decision.ALLOW, "audit:read", "audit", scopes=frozenset({"audit:read"})),
    Policy(Decision.ALLOW, "game:read", "game:*", scopes=frozenset({"game:read"})),
    Policy(Decision.ALLOW, "knowledge:recommend", "recommendation", scopes=frozenset({"game:read"})),
    Policy(Decision.ALLOW, "billing:read", "billing:*", scopes=frozenset({"game:read"})),
    Policy(Decision.ALLOW, "billing:write", "billing:*", scopes=frozenset({"game:read"})),
])
billing_service = BillingService(store)


class RateLimiter:
    """Process-local sliding-window rate limiter with bounded bucket count.

    Inactive buckets (no hits inside the active window) are evicted before a
    capacity check. Active buckets are never displaced to free capacity.
    """

    def __init__(self, limit: int = 120, window: int = 60, max_buckets: int | None = None) -> None:
        self.limit = limit
        self.window = window
        if max_buckets is None:
            max_buckets = int(os.getenv("RATE_LIMIT_MAX_BUCKETS", "10000"))
        self.max_buckets = max(1, max_buckets)
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _prune_inactive(self, now: float) -> None:
        inactive = [key for key, q in self._hits.items() if not q or q[-1] <= now - self.window]
        for key in inactive:
            del self._hits[key]

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits.get(key)
            if q is not None:
                while q and q[0] <= now - self.window:
                    q.popleft()
                if not q:
                    del self._hits[key]
                    q = None

            if q is None:
                if len(self._hits) >= self.max_buckets:
                    self._prune_inactive(now)
                if key not in self._hits and len(self._hits) >= self.max_buckets:
                    # Capacity reached; active buckets are preserved.
                    return False
                q = self._hits.setdefault(key, deque())

            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


rate_limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")))
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


def device_owned_by(principal: Principal, device: dict[str, Any], device_id: str) -> bool:
    return principal.device_id == device_id or device.get("user_id") == principal.user_id


# Phase 1 characters/game-state domain (issue #107)
install_game_state_routes(
    app,
    store=store,
    principal_from_token=principal_from_token,
    require_bearer=require_bearer,
    authorize_request=authorize_request,
    request_id=request_id,
)


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


@app.post("/v1/auth/register", response_model=SessionResponse)
def register_user(payload: RegisterRequest, request: Request):
    rate_limit(request, "auth-register")
    try:
        user_id = user_store.register(payload.email, payload.password)
    except Exception as exc:
        if "EMAIL_ALREADY_REGISTERED" in str(exc) or "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise HTTPException(status_code=409, detail="EMAIL_ALREADY_REGISTERED") from exc
        raise
    access, refresh, expires_at, scopes = store.issue_session(None, user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    user_store.restrict_session_scopes(store, access, {"character:read", "game:read", "audit:read"})
    scopes = ["character:read", "game:read", "audit:read"]
    store.add_audit({"actor_user_id": user_id, "actor_device_id": None, "action": "auth:register", "resource": "account", "decision": "ALLOW", "reason_code": "ACCOUNT_CREATED", "request_id": request_id(request)})
    verification_token = user_store.issue_action_token(payload.email, "EMAIL_VERIFY", 86_400)
    if verification_token:
        send_verification_email(email_transport, payload.email, verification_token)
    return SessionResponse(session_token=access, refresh_token=refresh, expires_at=expires_at, scopes=scopes)


@app.post("/v1/auth/email-verification/request", response_model=AuthActionResponse, status_code=202)
def request_email_verification(payload: EmailActionRequest, request: Request) -> AuthActionResponse:
    rate_limit(request, "auth-email-verification-request")
    token = user_store.issue_action_token(payload.email, "EMAIL_VERIFY", 86_400)
    if token:
        send_verification_email(email_transport, payload.email, token)
    return AuthActionResponse(status="ACCEPTED")


@app.post("/v1/auth/email-verification/confirm", response_model=AuthActionResponse)
def confirm_email_verification(payload: AuthTokenRequest, request: Request) -> AuthActionResponse:
    rate_limit(request, "auth-email-verification-confirm")
    if not user_store.confirm_email(payload.token):
        raise HTTPException(status_code=400, detail="AUTH_ACTION_TOKEN_INVALID")
    return AuthActionResponse(status="VERIFIED")


@app.post("/v1/auth/password-reset/request", response_model=AuthActionResponse, status_code=202)
def request_password_reset(payload: EmailActionRequest, request: Request) -> AuthActionResponse:
    rate_limit(request, "auth-password-reset-request")
    token = user_store.issue_action_token(payload.email, "PASSWORD_RESET", 1_800)
    if token:
        send_password_reset_email(email_transport, payload.email, token)
    return AuthActionResponse(status="ACCEPTED")


@app.post("/v1/auth/password-reset/confirm", response_model=AuthActionResponse)
def confirm_password_reset(payload: PasswordResetConfirmRequest, request: Request) -> AuthActionResponse:
    rate_limit(request, "auth-password-reset-confirm")
    if not user_store.reset_password(payload.token, payload.password, store):
        raise HTTPException(status_code=400, detail="AUTH_ACTION_TOKEN_INVALID")
    return AuthActionResponse(status="PASSWORD_UPDATED")


@app.get("/v1/account/security", response_model=AccountSecurityResponse)
def account_security(authorization_header: str = Header(..., alias="Authorization")) -> AccountSecurityResponse:
    principal = principal_from_token(require_bearer(authorization_header))
    state = user_store.security_state(principal.user_id)
    if not state:
        raise HTTPException(status_code=404, detail="ACCOUNT_NOT_FOUND")
    return AccountSecurityResponse(**state)


def _federated_error(exc: FederatedAuthError) -> HTTPException:
    code = str(exc)
    if code in {"AUTH_PROVIDER_NOT_CONFIGURED", "FEDERATED_PROVIDER_UNAVAILABLE"}:
        return HTTPException(status_code=503, detail=code)
    if code == "AUTH_PROVIDER_UNSUPPORTED":
        return HTTPException(status_code=404, detail=code)
    return HTTPException(status_code=400, detail=code)


def _federated_session(identity: VerifiedFederatedIdentity, request: Request) -> SessionResponse:
    user_id = user_store.external_identity_user(identity.provider, identity.subject)
    if user_id is None:
        try:
            user_id = user_store.register_external_account(
                identity.provider,
                identity.subject,
                email=identity.email,
                email_verified=identity.email_verified,
            )
        except ValueError as exc:
            if "ACCOUNT_LINK_REQUIRED" in str(exc):
                raise HTTPException(status_code=409, detail="ACCOUNT_LINK_REQUIRED") from exc
            raise
    access, refresh, expires_at, _ = store.issue_session(
        None,
        user_id,
        SESSION_TTL_SECONDS,
        REFRESH_TTL_SECONDS,
    )
    scopes = ["character:read", "game:read", "audit:read"]
    user_store.restrict_session_scopes(store, access, scopes)
    store.add_audit(
        {
            "actor_user_id": user_id,
            "actor_device_id": None,
            "action": "auth:federated-login",
            "resource": f"provider:{identity.provider}",
            "decision": "ALLOW",
            "reason_code": "FEDERATED_IDENTITY_VALID",
            "request_id": request_id(request),
        }
    )
    return SessionResponse(
        session_token=access,
        refresh_token=refresh,
        expires_at=expires_at,
        scopes=scopes,
    )


def _link_federated_identity(
    principal: Principal,
    identity: VerifiedFederatedIdentity,
    request: Request,
) -> AuthActionResponse:
    existing = user_store.external_identity_user(identity.provider, identity.subject)
    if existing and existing != principal.user_id:
        raise HTTPException(status_code=409, detail="EXTERNAL_IDENTITY_ALREADY_LINKED")
    if existing is None:
        try:
            user_store.link_external_identity(
                principal.user_id,
                identity.provider,
                identity.subject,
                identity.email,
            )
        except ValueError as exc:
            code = str(exc)
            if "PROVIDER_ALREADY_LINKED" in code or "EXTERNAL_IDENTITY_ALREADY_LINKED" in code:
                raise HTTPException(status_code=409, detail=code) from exc
            raise
    store.add_audit(
        {
            "actor_user_id": principal.user_id,
            "actor_device_id": principal.device_id,
            "action": "auth:provider-link",
            "resource": f"provider:{identity.provider}",
            "decision": "ALLOW",
            "reason_code": "FEDERATED_IDENTITY_VALID",
            "request_id": request_id(request),
        }
    )
    return AuthActionResponse(status="LINKED")


@app.get("/v1/auth/providers", response_model=FederatedProvidersResponse)
def federated_provider_catalog() -> FederatedProvidersResponse:
    return FederatedProvidersResponse(
        providers=[
            FederatedProviderStatusResponse(
                provider=item.provider,
                enabled=item.enabled,
                flow=item.flow,
                client_id=item.client_id,
            )
            for item in provider_statuses()
        ]
    )


@app.post("/v1/auth/providers/google/challenge", response_model=GoogleAuthChallengeResponse)
def google_auth_challenge(request: Request) -> GoogleAuthChallengeResponse:
    rate_limit(request, "auth-google-challenge")
    status = provider_status("google")
    if not status.enabled or not status.client_id:
        raise HTTPException(status_code=503, detail="AUTH_PROVIDER_NOT_CONFIGURED")
    nonce = user_store.issue_federated_challenge("google", "OIDC_NONCE", 300)
    return GoogleAuthChallengeResponse(client_id=status.client_id, nonce=nonce)


def _verified_google(payload: GoogleCredentialRequest) -> VerifiedFederatedIdentity:
    try:
        identity = verify_google_id_token(payload.id_token, payload.nonce)
    except FederatedAuthError as exc:
        raise _federated_error(exc) from exc
    consumed, _ = user_store.consume_federated_challenge("google", "OIDC_NONCE", payload.nonce)
    if not consumed:
        raise HTTPException(status_code=400, detail="FEDERATED_CHALLENGE_INVALID")
    return identity


@app.post("/v1/auth/providers/google/login", response_model=SessionResponse)
def google_federated_login(payload: GoogleCredentialRequest, request: Request) -> SessionResponse:
    rate_limit(request, "auth-google-login")
    return _federated_session(_verified_google(payload), request)


@app.post("/v1/account/providers/google/link", response_model=AuthActionResponse)
def google_provider_link(
    payload: GoogleCredentialRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
) -> AuthActionResponse:
    rate_limit(request, "auth-google-link")
    principal = principal_from_token(require_bearer(authorization_header))
    return _link_federated_identity(principal, _verified_google(payload), request)


@app.post("/v1/auth/providers/{provider}/start", response_model=BrowserAuthStartResponse)
def browser_federated_start(
    provider: str,
    payload: BrowserAuthStartRequest,
    request: Request,
) -> BrowserAuthStartResponse:
    rate_limit(request, f"auth-{provider}-start")
    normalized = provider.strip().lower()
    if normalized not in {"telegram", "vk"}:
        raise HTTPException(status_code=404, detail="AUTH_PROVIDER_UNSUPPORTED")
    try:
        state = user_store.issue_federated_challenge(
            normalized,
            "OAUTH_STATE",
            300,
            redirect_uri=payload.redirect_uri,
        )
        started = start_browser_flow(normalized, state, payload.redirect_uri)
    except FederatedAuthError as exc:
        raise _federated_error(exc) from exc
    return BrowserAuthStartResponse(
        provider=normalized,
        authorization_url=started.authorization_url,
        state=started.state,
        code_verifier=started.code_verifier,
    )


def _verified_browser(
    provider: str,
    payload: BrowserAuthCompleteRequest,
) -> VerifiedFederatedIdentity:
    normalized = provider.strip().lower()
    if normalized not in {"telegram", "vk"}:
        raise HTTPException(status_code=404, detail="AUTH_PROVIDER_UNSUPPORTED")
    consumed, redirect_uri = user_store.consume_federated_challenge(
        normalized,
        "OAUTH_STATE",
        payload.state,
    )
    if not consumed or not redirect_uri:
        raise HTTPException(status_code=400, detail="FEDERATED_CHALLENGE_INVALID")
    try:
        if normalized == "telegram":
            return complete_telegram(
                code=payload.code,
                code_verifier=payload.code_verifier,
                redirect_uri=redirect_uri,
                nonce=payload.state,
            )
        if not payload.device_id:
            raise FederatedAuthError("VK_DEVICE_ID_REQUIRED")
        return complete_vk(
            code=payload.code,
            state=payload.state,
            code_verifier=payload.code_verifier,
            device_id=payload.device_id,
            redirect_uri=redirect_uri,
        )
    except FederatedAuthError as exc:
        raise _federated_error(exc) from exc


@app.post("/v1/auth/providers/{provider}/complete", response_model=SessionResponse)
def browser_federated_complete(
    provider: str,
    payload: BrowserAuthCompleteRequest,
    request: Request,
) -> SessionResponse:
    rate_limit(request, f"auth-{provider}-complete")
    return _federated_session(_verified_browser(provider, payload), request)


@app.post("/v1/account/providers/{provider}/link", response_model=AuthActionResponse)
def browser_provider_link(
    provider: str,
    payload: BrowserAuthCompleteRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
) -> AuthActionResponse:
    rate_limit(request, f"auth-{provider}-link")
    principal = principal_from_token(require_bearer(authorization_header))
    return _link_federated_identity(principal, _verified_browser(provider, payload), request)


@app.post("/v1/auth/login", response_model=SessionResponse)
def login_user(payload: LoginRequest, request: Request):
    rate_limit(request, "auth-login")
    subject = payload.email.strip().lower()
    threshold = int(os.getenv("SENTINEL_AUTH_LOCKOUT_THRESHOLD", "8"))
    if subject and store.security_failure_count(subject) >= threshold:
        raise HTTPException(status_code=429, detail="AUTH_LOCKOUT")
    user_id = user_store.authenticate(payload.email, payload.password)
    if not user_id:
        if subject:
            store.record_security_failure(subject, "auth-login")
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")
    access, refresh, expires_at, scopes = store.issue_session(None, user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    user_store.restrict_session_scopes(store, access, {"character:read", "game:read", "audit:read"})
    scopes = ["character:read", "game:read", "audit:read"]
    store.add_audit({"actor_user_id": user_id, "actor_device_id": None, "action": "auth:login", "resource": "session", "decision": "ALLOW", "reason_code": "CREDENTIALS_VALID", "request_id": request_id(request)})
    return SessionResponse(session_token=access, refresh_token=refresh, expires_at=expires_at, scopes=scopes)


@app.post("/v1/devices/register", response_model=DeviceRegisterResponse)
def register_device(
    payload: DeviceRegisterRequest,
    request: Request,
    authorization_header: str | None = Header(default=None, alias="Authorization"),
    x_enrollment_token: str | None = Header(default=None, alias="X-Enrollment-Token"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    rid = request_id(request, x_request_id)
    rate_limit(request, "device-register")
    if authorization_header:
        principal = principal_from_token(require_bearer(authorization_header))
        user_id = principal.user_id
        if payload.user_id != user_id:
            raise HTTPException(status_code=403, detail="USER_SCOPE_MISMATCH")
    else:
        user_id = payload.user_id
        require_enrollment(x_enrollment_token, user_id)
    try:
        fingerprint = fingerprint_public_key(payload.public_key_der_b64)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="INVALID_PUBLIC_KEY") from exc
    if fingerprint.lower() != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail="FINGERPRINT_MISMATCH")
    challenge = secrets.token_urlsafe(32)
    device_id = store.register_device(user_id, payload.platform, payload.public_key_der_b64, fingerprint, challenge)
    return DeviceRegisterResponse(device_id=device_id, state="ACTIVE", challenge=challenge)


@app.post("/v1/devices/bind", response_model=DeviceRegisterResponse)
def bind_device(
    payload: DeviceBindRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    rid = request_id(request, x_request_id)
    rate_limit(request, "device-bind")
    token = require_bearer(authorization_header)
    principal = principal_from_token(token)
    try:
        fingerprint = fingerprint_public_key(payload.public_key_der_b64)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="INVALID_PUBLIC_KEY") from exc
    if fingerprint.lower() != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail="FINGERPRINT_MISMATCH")
    challenge = secrets.token_urlsafe(32)
    device_id = store.register_device(principal.user_id, payload.platform, payload.public_key_der_b64, fingerprint, challenge)
    bind_session_to_device(token, device_id)
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": device_id, "action": "device:bind", "resource": "device", "decision": "ALLOW", "reason_code": "DEVICE_BOUND_SESSION_LINKED", "request_id": rid})
    return DeviceRegisterResponse(device_id=device_id, state="ACTIVE", challenge=challenge)


@app.get("/v1/devices/{device_id}")
def get_device(device_id: str, authorization_header: str = Header(..., alias="Authorization")):
    principal = principal_from_token(require_bearer(authorization_header))
    device = store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    if device.get("user_id") != principal.user_id:
        raise HTTPException(status_code=403, detail="DEVICE_SCOPE_MISMATCH")
    return {
        "device_id": device_id,
        "state": device.get("state"),
        "platform": device.get("platform"),
        "fingerprint_sha256": device.get("fingerprint"),
        "algorithm": "EC / secp256r1 / SHA256withECDSA",
        "bound_at": None,
        "last_seen_at": None,
        "security_status": "SECURE" if device.get("state") == "ACTIVE" else "AT_RISK",
    }


@app.post("/v1/devices/{device_id}/revoke")
def revoke_device(device_id: str, request: Request, authorization_header: str = Header(..., alias="Authorization"), x_request_id: str | None = Header(default=None, alias="X-Request-ID")):
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    device = store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    if not device_owned_by(principal, device, device_id):
        raise HTTPException(status_code=403, detail="DEVICE_SCOPE_MISMATCH")
    if device.get("state") == "REVOKED":
        raise HTTPException(status_code=409, detail="DEVICE_ALREADY_REVOKED")
    set_device_state(device_id, "REVOKED")
    revoke_device_sessions(device_id)
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": device_id, "action": "device:revoke", "resource": "device", "decision": "ALLOW", "reason_code": "DEVICE_REVOKED", "request_id": rid})
    return {"revoked": True}


@app.post("/v1/devices/{device_id}/rotate")
def rotate_device(
    device_id: str,
    payload: DeviceBindRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    rid = request_id(request, x_request_id)
    token = require_bearer(authorization_header)
    principal = principal_from_token(token)
    device = store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    if not device_owned_by(principal, device, device_id):
        raise HTTPException(status_code=403, detail="DEVICE_SCOPE_MISMATCH")
    if device.get("state") != "ACTIVE":
        raise HTTPException(status_code=409, detail="DEVICE_NOT_ACTIVE")
    try:
        fingerprint = fingerprint_public_key(payload.public_key_der_b64)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="INVALID_PUBLIC_KEY") from exc
    if fingerprint.lower() != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail="FINGERPRINT_MISMATCH")
    if fingerprint.lower() == str(device.get("fingerprint", "")).lower():
        raise HTTPException(status_code=409, detail="KEY_UNCHANGED")

    challenge = secrets.token_urlsafe(32)
    new_device_id = store.register_device(principal.user_id, payload.platform, payload.public_key_der_b64, fingerprint, challenge)
    new_access, new_refresh, expires_at, scopes = store.issue_session(new_device_id, principal.user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    set_device_state(device_id, "REVOKED")
    revoke_device_sessions(device_id)
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": device_id, "action": "device:rotate", "resource": new_device_id, "decision": "ALLOW", "reason_code": "DEVICE_ROTATED", "request_id": rid})
    return {
        "device_id": new_device_id,
        "state": "ACTIVE",
        "challenge": challenge,
        "session_token": new_access,
        "refresh_token": new_refresh,
        "expires_at": expires_at,
        "scopes": scopes,
    }


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
    access, refresh, expires_at, scopes, previous = result
    if previous.get("device_id") is None:
        user_scopes = {"character:read", "game:read", "audit:read"}
        user_store.restrict_session_scopes(store, access, user_scopes)
        scopes = sorted(user_scopes)
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
        result = store.save_event_batch({"user_id": principal.user_id, "device_id": principal.device_id}, events, x_idempotency_key)
    except ValueError as exc:
        code = str(exc)
        status = 409 if code in {"SEQUENCE_REPLAY", "IDEMPOTENCY_KEY_REUSE"} else 403
        raise HTTPException(status_code=status, detail=code) from exc
    # Phase 2 (#107): project character.* events into characters store.
    # Projection is best-effort relative to the durable event log; invalid
    # payloads are skipped without failing the batch.
    if result.get("accepted", 0) > 0:
        apply_character_projections(store, principal.user_id, events)
    return result


@app.get("/v1/audit")
def audit(authorization_header: str = Header(..., alias="Authorization")):
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "audit:read", "audit", str(uuid.uuid4()))
    return {"events": store.get_audit(principal.user_id)}


@app.get("/v1/admin/games")
def admin_games(request: Request, x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    rate_limit(request, "admin")
    require_admin(x_sentinel_admin_token, request, store)
    return {"games": [game.__dict__ for game in DIABLO_CATALOG]}


@app.get("/v1/admin/entitlements")
def admin_entitlements(request: Request, x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    rate_limit(request, "admin")
    require_admin(x_sentinel_admin_token, request, store)
    return {"entitlements": store.list_entitlements()}


@app.post("/v1/admin/entitlements")
def admin_create_entitlement(payload: AdminEntitlementRequest, request: Request, x_sentinel_admin_token: str | None = Header(default=None)) -> dict:
    rate_limit(request, "admin")
    require_admin(x_sentinel_admin_token, request, store)
    if get_game(payload.game_id) is None:
        raise HTTPException(status_code=404, detail="GAME_NOT_FOUND")
    if payload.valid_until < payload.valid_from:
        raise HTTPException(status_code=400, detail="INVALID_ENTITLEMENT_WINDOW")
    item = {"id": str(uuid.uuid4()), "user_id": payload.user_id, "game_id": payload.game_id, "source": payload.source, "status": EntitlementStatus.ACTIVE, "valid_from": payload.valid_from, "valid_until": payload.valid_until}
    store.create_entitlement(item)
    store.add_audit({"actor_user_id": payload.user_id, "actor_device_id": None, "action": "admin:entitlement:create", "resource": payload.game_id, "decision": "ALLOW", "reason_code": "ADMIN_GRANT", "request_id": None})
    return item


@app.get("/v1/billing/plans")
def billing_plans(
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, Any]:
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "billing:read", "billing:plans", rid)
    return {"plans": billing_service.plans()}


@app.get("/v1/billing/subscriptions")
def billing_subscriptions(
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, Any]:
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "billing:read", "billing:subscriptions", rid)
    return {"subscriptions": store.list_subscriptions(principal.user_id)}


@app.post("/v1/billing/subscriptions")
def create_billing_subscription(
    payload: BillingSubscriptionRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, Any]:
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "billing:write", "billing:subscriptions", rid)
    try:
        item = billing_service.create_subscription(
            principal.user_id,
            payload.plan_code,
            provider=payload.provider,
            provider_subscription_id=payload.provider_subscription_id,
        )
    except ValueError as exc:
        code = str(exc)
        status = 409 if code == "SUBSCRIPTION_ALREADY_EXISTS" else 400
        raise HTTPException(status_code=status, detail=code) from exc
    store.add_audit({
        "actor_user_id": principal.user_id,
        "actor_device_id": principal.device_id,
        "action": "billing:subscription:create",
        "resource": item["id"],
        "decision": "ALLOW",
        "reason_code": "SUBSCRIPTION_PENDING",
        "request_id": rid,
    })
    return item


@app.post("/v1/billing/webhooks/{provider}")
def billing_webhook(
    provider: str,
    payload: BillingWebhookRequest,
    request: Request,
    x_billing_webhook_token: str | None = Header(default=None, alias="X-Billing-Webhook-Token"),
) -> dict[str, Any]:
    configured = os.getenv("SENTINEL_BILLING_WEBHOOK_TOKEN", "")
    if not configured:
        raise HTTPException(status_code=503, detail="BILLING_WEBHOOK_NOT_CONFIGURED")
    if not x_billing_webhook_token or not secrets.compare_digest(x_billing_webhook_token, configured):
        raise HTTPException(status_code=401, detail="INVALID_BILLING_WEBHOOK_TOKEN")
    try:
        result = billing_service.apply_webhook(
            BillingWebhookEvent(
                event_id=payload.event_id,
                provider=provider,
                provider_subscription_id=payload.provider_subscription_id,
                target_state=BillingState(payload.status),
                occurred_at=payload.occurred_at,
                external_reference=payload.external_reference,
                payload=payload.payload,
            )
        )
    except ValueError as exc:
        code = str(exc)
        status = 404 if code == "SUBSCRIPTION_NOT_FOUND" else 409 if code in {"SUBSCRIPTION_STATE_CHANGED", "INVALID_WEBHOOK_STATE"} else 400
        raise HTTPException(status_code=status, detail=code) from exc
    subscription = result["subscription"]
    store.add_audit({
        "actor_user_id": subscription.get("user_id"),
        "actor_device_id": None,
        "action": "billing:webhook:apply",
        "resource": subscription["id"],
        "decision": "ALLOW",
        "reason_code": "BILLING_EVENT_DUPLICATE" if result["duplicate"] else "BILLING_EVENT_ACCEPTED",
        "request_id": request_id(request),
    })
    return result


@app.post("/v1/integrity/nonce")
def issue_integrity_nonce(request: Request, authorization_header: str = Header(..., alias="Authorization")) -> dict[str, str]:
    rate_limit(request, "integrity-nonce")
    principal_from_token(require_bearer(authorization_header))
    nonce = integrity_nonces.issue()
    return {"nonce": nonce, "ttl_seconds": str(integrity_nonces.ttl_seconds)}


@app.post("/v1/integrity/attest")
def attest_integrity(payload: dict[str, object], request: Request, authorization_header: str = Header(..., alias="Authorization")) -> dict[str, object]:
    rate_limit(request, "integrity-attest")
    principal_from_token(require_bearer(authorization_header))
    nonce = str(payload.get("nonce") or "")
    if not integrity_nonces.consume(nonce):
        raise HTTPException(status_code=401, detail="INTEGRITY_NONCE_INVALID")
    token = str(payload.get("integrity_token") or "")
    if not token:
        raise HTTPException(status_code=401, detail="INTEGRITY_TOKEN_REQUIRED")
    # Client verdicts are deliberately ignored; only the server verifier may establish trust.
    result = play_integrity.verify(token, nonce)
    return {
        "tier": result.tier.value,
        "reason": result.reason,
        "trusted": result.trusted,
        "package_name": result.package_name,
    }


@app.post("/v1/recommendations", response_model=RecommendationResponse)
def recommendations(payload: RecommendationRequest, request: Request, authorization_header: str = Header(..., alias="Authorization"), x_request_id: str | None = Header(default=None, alias="X-Request-ID")):
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "knowledge:recommend", "recommendation", rid)
    result = [Recommendation(kind="recommendation", text="Review the most recent character events before making a progression decision.", confidence=0.72, provenance=["sentinel-core:context-baseline"])]
    return RecommendationResponse(recommendations=result)
