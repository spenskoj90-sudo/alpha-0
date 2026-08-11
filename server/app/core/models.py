from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class DeviceRegisterRequest(BaseModel):
    user_id: str
    platform: Literal["android"]
    public_key_der_b64: str
    fingerprint_sha256: str


class DeviceRegisterResponse(BaseModel):
    device_id: str
    state: Literal["ACTIVE"]
    challenge: str


class DeviceProofRequest(BaseModel):
    challenge: str
    timestamp: int
    request_id: str
    signature_b64: str


class SessionResponse(BaseModel):
    session_token: str
    expires_at: datetime
    scopes: list[str]


class AuthorizeRequest(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    resource: str = Field(min_length=1, max_length=500)


class AuthorizeResponse(BaseModel):
    decision: Literal["ALLOW", "DENY"]
    reason_code: str


class GameEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    device_id: str
    type: str
    schema_version: int = Field(ge=1)
    occurred_at: datetime
    sequence: int = Field(ge=0)
    payload: dict[str, Any]


class EventBatchRequest(BaseModel):
    events: list[GameEvent] = Field(min_length=1, max_length=100)


class RecommendationRequest(BaseModel):
    context: dict[str, Any]


class Recommendation(BaseModel):
    kind: Literal["fact", "inference", "recommendation"]
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: list[str]


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
