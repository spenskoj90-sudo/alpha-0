from __future__ import annotations

from base64 import b64decode
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .config import settings
from .device_identity import verify_registration
from .engines import AuditSystem, EntitlementEngine, KnowledgeEngine, KnowledgeKind
from .security import AuthzContext, AuthorizationEngine, Policy
from .session import SessionProtocol

app = FastAPI(title=settings.app_name, version="0.1.0")

session_protocol = SessionProtocol(settings.session_ttl_seconds, settings.challenge_ttl_seconds)
audit = AuditSystem()
entitlements = EntitlementEngine()
knowledge = KnowledgeEngine()
authz = AuthorizationEngine((
    Policy("device.read", frozenset({"user"})),
    Policy("device.revoke", frozenset({"user"})),
    Policy("character.read", frozenset({"user"}), frozenset({"character:read"})),
    Policy("knowledge.read", frozenset({"user"}), frozenset({"knowledge:read"})),
))
# Development enrollment registry. Production must replace this with PostgreSQL-backed enrollment.
devices: dict[UUID, tuple[UUID, bytes]] = {}


class DeviceRegistration(BaseModel):
    user_id: UUID
    public_key_spki: str = Field(min_length=1, max_length=8192)
    fingerprint_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    platform: str = Field(min_length=1, max_length=32)


class DeviceRegistrationResponse(BaseModel):
    device_id: UUID
    status: str
    key_version: int


class ChallengeRequest(BaseModel):
    device_id: UUID


class ChallengeResponse(BaseModel):
    session_id: UUID
    challenge: str
    expires_at: str


class VerifyRequest(BaseModel):
    session_id: UUID
    device_id: UUID
    signature: str
    request_hash: str


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    session_id: UUID


class KnowledgeResponse(BaseModel):
    kind: str
    statement: str
    confidence: float
    provenance: list[str]


@app.middleware("http")
async def request_limits(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_body_bytes:
        raise HTTPException(status_code=413, detail="request too large")
    return await call_next(request)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    return {"status": "ok", "mode": settings.environment}


@app.post("/v1/devices", response_model=DeviceRegistrationResponse)
def register_device(payload: DeviceRegistration, enrollment_token: str | None = Header(default=None, alias="X-Enrollment-Token")):
    if settings.environment == "production" or not enrollment_token:
        raise HTTPException(status_code=403, detail="enrollment disabled")
    if enrollment_token != "development-only-enrollment":
        raise HTTPException(status_code=403, detail="invalid enrollment token")
    try:
        spki = verify_registration(payload.public_key_spki, payload.fingerprint_sha256)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    device_id = uuid4()
    devices[device_id] = (payload.user_id, spki)
    return DeviceRegistrationResponse(device_id=device_id, status="ACTIVE", key_version=1)


@app.post("/v1/sessions/challenge", response_model=ChallengeResponse)
def create_challenge(payload: ChallengeRequest):
    if payload.device_id not in devices:
        raise HTTPException(status_code=404, detail="device not found")
    challenge = session_protocol.issue_challenge(payload.device_id)
    return ChallengeResponse(session_id=challenge.session_id, challenge=challenge.nonce, expires_at=challenge.expires_at.isoformat())


@app.post("/v1/sessions/verify", response_model=SessionResponse)
def verify_session(payload: VerifyRequest):
    device = devices.get(payload.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    try:
        signature = b64decode(payload.signature, validate=True)
        request_hash = bytes.fromhex(payload.request_hash)
        token = session_protocol.verify(payload.session_id, payload.device_id, device[1], signature, request_hash)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="session verification failed") from exc
    return SessionResponse(access_token=token, expires_in=settings.session_ttl_seconds, session_id=payload.session_id)


def require_session(authorization: str | None = Header(default=None)) -> tuple[UUID, UUID]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        return session_protocol.validate(authorization.removeprefix("Bearer ").strip())
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid session") from exc


@app.get("/v1/me/devices")
def list_devices(session: tuple[UUID, UUID] = Depends(require_session)):
    _, device_id = session
    user_id, _ = devices[device_id]
    return [{"device_id": str(device_id), "user_id": str(user_id), "status": "ACTIVE"}]


@app.get("/v1/knowledge", response_model=list[KnowledgeResponse])
def get_knowledge(session: tuple[UUID, UUID] = Depends(require_session)):
    _, device_id = session
    user_id, _ = devices[device_id]
    ctx = AuthzContext(str(user_id), str(device_id), frozenset({"user"}), frozenset({"knowledge:read"}), frozenset())
    if not authz.authorize(ctx, "knowledge.read"):
        audit.record(user_id, "knowledge.read", f"user:{user_id}", "DENY", uuid4())
        raise HTTPException(status_code=403, detail="access denied")
    item = knowledge.build(KnowledgeKind.FACT, "SENTINEL Core is authoritative for canonical state.", 0.99, ["architecture"])
    return [KnowledgeResponse(kind=item.kind.value, statement=item.statement, confidence=item.confidence, provenance=list(item.provenance))]
