from datetime import UTC, datetime

import pytest

from app.core.companion_experience import (
    CompanionExperienceRuntime,
    VoiceBoundary,
    VoiceBoundaryError,
    VoiceReasonCode,
)
from app.core.companion_peer_auth import AllowlistPeerAuthenticator, PeerAuthEvidence
from app.core.companion_protocol import (
    CompanionEnvelope,
    CompanionMessageType,
    LatencyClass,
)
from app.core.companion_runtime import CompanionRuntime
from app.core.companion_transport import CompanionTransportSession


NOW = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)


def connected_runtime() -> CompanionExperienceRuntime:
    session = CompanionTransportSession(
        CompanionRuntime(),
        peer_authenticator=AllowlistPeerAuthenticator({"android-1"}),
    )
    session.connect(
        NOW,
        auth_evidence=PeerAuthEvidence(mechanism="test-mtls", peer_id="android-1", authenticated=True),
    )
    return CompanionExperienceRuntime(session)


def update_envelope() -> CompanionEnvelope:
    return CompanionEnvelope(
        sequence=1,
        message_type=CompanionMessageType.UGS_UPDATE,
        latency_class=LatencyClass.RESPONSIVE,
        payload={
            "event_id": "companion-wow-1",
            "observed_at": NOW.isoformat(),
            "patch_profile": "wotlk-3.3.5a",
            "server_profile": "private",
            "account_entitled": "true",
            "addon_connected": "true",
        },
    )


def test_authenticated_update_composes_state_recommendation_health_and_presentation() -> None:
    runtime = connected_runtime()
    snapshot = runtime.process_update(update_envelope(), session_id="session-1", now=NOW)

    assert snapshot.vertical.accepted is True
    assert snapshot.recommendation.recommendations
    assert snapshot.presentations[0].kind.value == "STATUS"
    assert any(item.kind.value == "RECOMMENDATION" for item in snapshot.presentations)
    assert snapshot.entitlement is True
    assert "wow-3.3.5a:external-environment-unverified" in snapshot.capability_claims
    assert runtime.enqueue_presentations(snapshot) == len(snapshot.presentations)

    queued: list[CompanionEnvelope] = []
    while (item := runtime.session.queue.pop()) is not None:
        queued.append(item)
    assert queued
    assert {item.message_type for item in queued} == {CompanionMessageType.PRESENTATION}


def test_experience_requires_authenticated_transport() -> None:
    runtime = CompanionExperienceRuntime(CompanionTransportSession(CompanionRuntime()))
    with pytest.raises(PermissionError, match="PEER_AUTHENTICATION_REQUIRED"):
        runtime.process_update(update_envelope(), session_id="session-1", now=NOW)


def test_voice_boundary_is_bounded_and_action_fail_closed() -> None:
    class StubStt:
        def transcribe(self, audio: bytes, *, locale: str) -> str:
            assert audio == b"audio"
            return "acknowledge"

    class StubTts:
        def synthesize(self, text: str, *, locale: str) -> bytes:
            return text.encode()

    voice = VoiceBoundary(stt=StubStt(), tts=StubTts())
    transcript = voice.transcribe(b"audio", locale="en", consent_granted=True)
    command = voice.classify(transcript, recommendation_id="rec-1")
    assert command.accepted is True
    assert command.intent is not None and command.intent.mode.value == "ACKNOWLEDGE"
    assert voice.synthesize("status", locale="en", consent_granted=True) == b"status"

    denied = voice.classify("attack target", recommendation_id="rec-1")
    assert denied.accepted is False
    assert denied.reason_code is VoiceReasonCode.ACTION_GATEWAY_REQUIRED

    with pytest.raises(VoiceBoundaryError, match=VoiceReasonCode.CONSENT_REQUIRED.value):
        voice.transcribe(b"audio", locale="en", consent_granted=False)
