from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .companion_experience import VoiceBoundary, VoiceBoundaryError, VoiceReasonCode

router = APIRouter(tags=["companion-voice"])

_AUDIO_B64_MAX = 700_000
_RECOMMENDATION_ID_PATTERN = r"^[A-Za-z0-9._:-]+$"
_LOCALE_PATTERN = r"^[A-Za-z0-9-]+$"
_CAPTURE_CONTENT_TYPE = "audio/webm;codecs=opus"
_SYNTHESIS_CONTENT_TYPE = "audio/wav"


class VoiceTranscribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio_b64: str = Field(min_length=1, max_length=_AUDIO_B64_MAX)
    locale: str = Field(default="en", min_length=2, max_length=16, pattern=_LOCALE_PATTERN)
    recommendation_id: str = Field(min_length=1, max_length=128, pattern=_RECOMMENDATION_ID_PATTERN)
    consent_granted: bool


class VoiceSynthesizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2_000)
    locale: str = Field(default="en", min_length=2, max_length=16, pattern=_LOCALE_PATTERN)
    consent_granted: bool


def _boundary(request: Request) -> VoiceBoundary:
    configured = getattr(request.app.state, "companion_voice_boundary", None)
    if isinstance(configured, VoiceBoundary):
        return configured
    from .companion_voice_provider import configured_voice_boundary

    boundary = configured_voice_boundary()
    request.app.state.companion_voice_boundary = boundary
    return boundary


def _security_context():
    from app.main import (
        authorize_request,
        billing_service,
        principal_from_token,
        rate_limit,
        request_id,
        require_bearer,
        store,
    )
    return authorize_request, billing_service, principal_from_token, rate_limit, request_id, require_bearer, store


def _require_voice_access(request: Request, authorization_header: str, supplied_request_id: str | None):
    authorize_request, billing_service, principal_from_token, rate_limit, request_id, require_bearer, store = _security_context()
    rate_limit(request, "companion-voice")
    rid = request_id(request, supplied_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "game:read", "game:companion-voice", rid)
    if not billing_service.has_feature(principal.user_id, "companion"):
        store.add_audit({
            "actor_user_id": principal.user_id,
            "actor_device_id": principal.device_id,
            "action": "companion:voice",
            "resource": "voice",
            "decision": "DENY",
            "reason_code": "COMPANION_ENTITLEMENT_REQUIRED",
            "request_id": rid,
        })
        raise HTTPException(status_code=403, detail="COMPANION_ENTITLEMENT_REQUIRED")
    return principal, rid, store


def _audit(store: Any, principal: Any, *, action: str, decision: str, reason_code: str, request_id: str) -> None:
    store.add_audit({
        "actor_user_id": principal.user_id,
        "actor_device_id": principal.device_id,
        "action": action,
        "resource": "companion-voice",
        "decision": decision,
        "reason_code": reason_code,
        "request_id": request_id,
    })


def _raise_voice_boundary(error: VoiceBoundaryError, *, store: Any, principal: Any, action: str, rid: str) -> None:
    code = str(error)
    status = {
        VoiceReasonCode.CONSENT_REQUIRED.value: 403,
        VoiceReasonCode.AUDIO_INVALID.value: 400,
        VoiceReasonCode.AUDIO_TOO_LARGE.value: 413,
        VoiceReasonCode.TEXT_TOO_LARGE.value: 400,
        VoiceReasonCode.PROVIDER_UNAVAILABLE.value: 503,
        VoiceReasonCode.PROVIDER_FAILED.value: 502,
        VoiceReasonCode.SYNTHESIZED_AUDIO_TOO_LARGE.value: 502,
    }.get(code, 400)
    _audit(store, principal, action=action, decision="DENY", reason_code=code, request_id=rid)
    raise HTTPException(status_code=status, detail=code) from error


@router.get("/v1/companion/voice/status")
def voice_status(
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, object]:
    principal, rid, store = _require_voice_access(request, authorization_header, x_request_id)
    boundary = _boundary(request)
    _audit(store, principal, action="companion:voice:status", decision="ALLOW", reason_code="VOICE_STATUS_READ", request_id=rid)
    return {
        "stt_available": boundary.stt is not None,
        "tts_available": boundary.tts is not None,
        "capture_content_type": _CAPTURE_CONTENT_TYPE,
        "synthesis_content_type": _SYNTHESIS_CONTENT_TYPE,
        "max_audio_bytes": boundary.config.max_audio_bytes,
        "max_text_chars": boundary.config.max_text_chars,
        "max_synthesized_bytes": boundary.config.max_synthesized_bytes,
        "action_capable": False,
        "request_id": rid,
    }


@router.post("/v1/companion/voice/transcribe")
def voice_transcribe(
    payload: VoiceTranscribeRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, object]:
    principal, rid, store = _require_voice_access(request, authorization_header, x_request_id)
    boundary = _boundary(request)
    if not payload.consent_granted:
        _raise_voice_boundary(
            VoiceBoundaryError(VoiceReasonCode.CONSENT_REQUIRED.value),
            store=store,
            principal=principal,
            action="companion:voice:transcribe",
            rid=rid,
        )
    try:
        audio = base64.b64decode(payload.audio_b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        _audit(store, principal, action="companion:voice:transcribe", decision="DENY", reason_code=VoiceReasonCode.AUDIO_INVALID.value, request_id=rid)
        raise HTTPException(status_code=400, detail=VoiceReasonCode.AUDIO_INVALID.value) from exc
    try:
        transcript = boundary.transcribe(audio, locale=payload.locale, consent_granted=True)
    except VoiceBoundaryError as exc:
        _raise_voice_boundary(exc, store=store, principal=principal, action="companion:voice:transcribe", rid=rid)
    result = boundary.classify(
        transcript,
        recommendation_id=payload.recommendation_id,
        locale=payload.locale,
    )
    _audit(
        store,
        principal,
        action="companion:voice:transcribe",
        decision="ALLOW" if result.accepted else "DENY",
        reason_code=result.reason_code.value,
        request_id=rid,
    )
    return {
        "accepted": result.accepted,
        "reason_code": result.reason_code.value,
        "intent": result.intent.model_dump(mode="json") if result.intent is not None else None,
        "action_capable": False,
        "request_id": rid,
    }


@router.post("/v1/companion/voice/synthesize")
def voice_synthesize(
    payload: VoiceSynthesizeRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, object]:
    principal, rid, store = _require_voice_access(request, authorization_header, x_request_id)
    boundary = _boundary(request)
    try:
        audio = boundary.synthesize(payload.text, locale=payload.locale, consent_granted=payload.consent_granted)
    except VoiceBoundaryError as exc:
        _raise_voice_boundary(exc, store=store, principal=principal, action="companion:voice:synthesize", rid=rid)
    _audit(store, principal, action="companion:voice:synthesize", decision="ALLOW", reason_code="VOICE_SYNTHESIS_ACCEPTED", request_id=rid)
    return {
        "audio_b64": base64.b64encode(audio).decode("ascii"),
        "content_type": _SYNTHESIS_CONTENT_TYPE,
        "bytes": len(audio),
        "action_capable": False,
        "request_id": rid,
    }
