from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.billing import BillingWebhookEvent
from app.core.companion_experience import VoiceBoundary
from app.core.p1_runtime import BillingState
from app.main import app, billing_service, principal_from_token, store


client = TestClient(app, client=("127.0.0.1", 43210))


class StubStt:
    def __init__(self, transcript: str = "acknowledge", *, fail: bool = False) -> None:
        self.transcript = transcript
        self.fail = fail
        self.calls: list[tuple[bytes, str]] = []

    def transcribe(self, audio: bytes, *, locale: str) -> str:
        self.calls.append((audio, locale))
        if self.fail:
            raise RuntimeError("provider exploded")
        return self.transcript


class StubTts:
    def __init__(self, payload: bytes = b"RIFF-test-wav", *, fail: bool = False) -> None:
        self.payload = payload
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def synthesize(self, text: str, *, locale: str) -> bytes:
        self.calls.append((text, locale))
        if self.fail:
            raise RuntimeError("provider exploded")
        return self.payload


@pytest.fixture(autouse=True)
def reset_voice_boundary():
    previous = getattr(app.state, "companion_voice_boundary", None)
    if hasattr(app.state, "companion_voice_boundary"):
        delattr(app.state, "companion_voice_boundary")
    yield
    if previous is None:
        if hasattr(app.state, "companion_voice_boundary"):
            delattr(app.state, "companion_voice_boundary")
    else:
        app.state.companion_voice_boundary = previous


def _register(*, entitled: bool) -> tuple[str, str]:
    suffix = uuid.uuid4().hex
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"voice-{suffix}@example.com",
            "password": f"Correct-Horse-Battery-Staple-{suffix}",
        },
    )
    assert response.status_code == 200
    token = response.json()["session_token"]
    principal = principal_from_token(token)
    assert "game:write" not in principal.scopes
    if entitled:
        provider_subscription_id = f"voice-{suffix}"
        billing_service.create_subscription(
            principal.user_id,
            "core-plus",
            provider="test",
            provider_subscription_id=provider_subscription_id,
        )
        billing_service.apply_webhook(
            BillingWebhookEvent(
                event_id=f"voice-event-{suffix}",
                provider="test",
                provider_subscription_id=provider_subscription_id,
                target_state=BillingState.ACTIVE,
                occurred_at=datetime.now(UTC),
            )
        )
    return token, principal.user_id


def _headers(token: str, request_id: str = "voice-test-request") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Request-ID": request_id}


def _transcribe_payload(audio: bytes = b"voice-audio", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "audio_b64": base64.b64encode(audio).decode("ascii"),
        "locale": "en",
        "recommendation_id": "rec-voice-1",
        "consent_granted": True,
    }
    payload.update(overrides)
    return payload


def test_voice_status_requires_session_and_active_companion_entitlement() -> None:
    assert client.get("/v1/companion/voice/status").status_code == 422
    token, _ = _register(entitled=False)
    denied = client.get("/v1/companion/voice/status", headers=_headers(token))
    assert denied.status_code == 403
    assert denied.json()["code"] == "COMPANION_ENTITLEMENT_REQUIRED"


def test_voice_status_is_bounded_and_never_exposes_provider_credentials() -> None:
    token, _ = _register(entitled=True)
    app.state.companion_voice_boundary = VoiceBoundary(stt=StubStt(), tts=StubTts())

    response = client.get("/v1/companion/voice/status", headers=_headers(token))
    assert response.status_code == 200
    payload = response.json()
    assert payload["stt_available"] is True
    assert payload["tts_available"] is True
    assert payload["capture_content_type"] == "audio/webm;codecs=opus"
    assert payload["synthesis_content_type"] == "audio/wav"
    assert payload["action_capable"] is False
    assert payload["max_audio_bytes"] == 512_000
    assert set(payload) == {
        "stt_available",
        "tts_available",
        "capture_content_type",
        "synthesis_content_type",
        "max_audio_bytes",
        "max_text_chars",
        "max_synthesized_bytes",
        "action_capable",
        "request_id",
    }


def test_transcribe_requires_explicit_consent_and_does_not_audit_voice_content() -> None:
    token, user_id = _register(entitled=True)
    stt = StubStt()
    app.state.companion_voice_boundary = VoiceBoundary(stt=stt)

    denied = client.post(
        "/v1/companion/voice/transcribe",
        headers=_headers(token, "voice-consent-denied"),
        json=_transcribe_payload(consent_granted=False),
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "VOICE_CONSENT_REQUIRED"
    assert stt.calls == []

    serialized_audit = str(store.get_audit(user_id))
    assert "voice-audio" not in serialized_audit
    assert "acknowledge" not in serialized_audit


def test_transcribe_classifies_presentation_intent_server_side_without_returning_transcript() -> None:
    token, user_id = _register(entitled=True)
    stt = StubStt("acknowledge")
    app.state.companion_voice_boundary = VoiceBoundary(stt=stt)

    response = client.post(
        "/v1/companion/voice/transcribe",
        headers=_headers(token, "voice-accepted"),
        json=_transcribe_payload(b"bounded-audio"),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["reason_code"] == "VOICE_ACCEPTED"
    assert payload["intent"] == {
        "surface": "VOICE",
        "mode": "ACKNOWLEDGE",
        "recommendation_id": "rec-voice-1",
        "locale": "en",
    }
    assert payload["action_capable"] is False
    assert "transcript" not in payload
    assert stt.calls == [(b"bounded-audio", "en")]

    audits = store.get_audit(user_id)
    assert any(
        item.get("action") == "companion:voice:transcribe"
        and item.get("reason_code") == "VOICE_ACCEPTED"
        and item.get("request_id") == "voice-accepted"
        for item in audits
    )
    assert "acknowledge" not in str(audits)


def test_action_like_voice_is_fail_closed_without_game_action_authority() -> None:
    token, _ = _register(entitled=True)
    app.state.companion_voice_boundary = VoiceBoundary(stt=StubStt("attack target"))

    response = client.post(
        "/v1/companion/voice/transcribe",
        headers=_headers(token),
        json=_transcribe_payload(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "accepted": False,
        "reason_code": "ACTION_GATEWAY_REQUIRED",
        "intent": None,
        "action_capable": False,
        "request_id": "voice-test-request",
    }


def test_invalid_audio_and_provider_failure_are_bounded_errors() -> None:
    token, _ = _register(entitled=True)
    app.state.companion_voice_boundary = VoiceBoundary(stt=StubStt())
    malformed = client.post(
        "/v1/companion/voice/transcribe",
        headers=_headers(token),
        json={**_transcribe_payload(), "audio_b64": "***not-base64***"},
    )
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "VOICE_AUDIO_INVALID"

    app.state.companion_voice_boundary = VoiceBoundary(stt=StubStt(fail=True))
    failed = client.post(
        "/v1/companion/voice/transcribe",
        headers=_headers(token),
        json=_transcribe_payload(),
    )
    assert failed.status_code == 502
    assert failed.json()["code"] == "VOICE_PROVIDER_FAILED"


def test_synthesis_is_consent_gated_and_returns_only_bounded_audio_metadata() -> None:
    token, user_id = _register(entitled=True)
    tts = StubTts()
    app.state.companion_voice_boundary = VoiceBoundary(tts=tts)

    denied = client.post(
        "/v1/companion/voice/synthesize",
        headers=_headers(token),
        json={"text": "Acknowledged.", "locale": "en", "consent_granted": False},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "VOICE_CONSENT_REQUIRED"
    assert tts.calls == []

    response = client.post(
        "/v1/companion/voice/synthesize",
        headers=_headers(token, "voice-tts"),
        json={"text": "Acknowledged.", "locale": "en", "consent_granted": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert base64.b64decode(payload["audio_b64"]) == b"RIFF-test-wav"
    assert payload["content_type"] == "audio/wav"
    assert payload["bytes"] == len(b"RIFF-test-wav")
    assert payload["action_capable"] is False
    assert "Acknowledged." not in str(store.get_audit(user_id))
