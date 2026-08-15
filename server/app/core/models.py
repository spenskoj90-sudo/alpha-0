from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class UserCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("INVALID_EMAIL")
        return normalized


class RegisterRequest(UserCredentials):
    pass


class LoginRequest(UserCredentials):
    pass


class DeviceRegisterRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:@-]+$")
    platform: Literal["android"]
    public_key_der_b64: str = Field(min_length=32, max_length=4096)
    fingerprint_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")


class DeviceRegisterResponse(BaseModel):
    device_id: str
    state: Literal["ACTIVE"]
    challenge: str


class DeviceProofRequest(BaseModel):
    challenge: str = Field(min_length=16, max_length=512)
    timestamp: int
    request_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    signature_b64: str = Field(min_length=16, max_length=4096)


class SessionResponse(BaseModel):
    session_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class AuthorizeRequest(BaseModel):
    action: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")
    resource: str = Field(min_length=1, max_length=500, pattern=r"^[A-Za-z0-9._:/*-]+$")


class AuthorizeResponse(BaseModel):
    decision: Literal["ALLOW", "DENY"]
    reason_code: str


class GameEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=8, max_length=128)
    device_id: str = Field(min_length=8, max_length=128)
    type: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    schema_version: int = Field(ge=1, le=1000)
    occurred_at: datetime
    sequence: int = Field(ge=0)
    payload: dict[str, Any]


class EventBatchRequest(BaseModel):
    events: list[GameEvent] = Field(min_length=1, max_length=100)


class RecommendationRequest(BaseModel):
    context: dict[str, Any] = Field(max_length=100)


class Recommendation(BaseModel):
    kind: Literal["fact", "inference", "recommendation"]
    text: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: list[str] = Field(max_length=20)


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]


class AdminEntitlementRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:@-]+$")
    game_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    source: str = Field(min_length=1, max_length=256)
    valid_from: datetime
    valid_until: datetime
