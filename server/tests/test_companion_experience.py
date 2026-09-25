from datetime import UTC, datetime

import pytest

from app.core.companion_experience import (
    CompanionExperienceRuntime,
    VoiceBoundary,
    VoiceBoundaryError,
    VoiceConfig,
    VoiceReasonCode,
    _payload_bool,
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


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_audio_bytes": 0},
        {"max_text_chars": 0},
        {"max_synthesized_bytes": 0},
    ],
)
def test_voice_config_rejects_nonpositive_resource_limits(kwargs) -> None:
    with pytest.raises(ValueError, match="voice limits must be positive"):
        VoiceConfig(**kwargs)


class _Stt:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = []

    def transcribe(self, audio: bytes, *, locale: str) -> str:
        self.calls.append((audio, locale))
        if self.error is not None:
            raise self.error
        return self.result


class _Tts:
    def __init__(self, result=b"wav", error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = []

    def synthesize(self, text: str, *, locale: str) -> bytes:
        self.calls.append((text, locale))
        if self.error is not None:
            raise self.error
        return self.result


@pytest.mark.parametrize(
    ("audio", "stt", "consent", "reason"),
    [
        (b"", _Stt("ok"), True, VoiceReasonCode.AUDIO_INVALID),
        (b"12345", _Stt("ok"), True, VoiceReasonCode.AUDIO_TOO_LARGE),
        (b"x", None, True, VoiceReasonCode.PROVIDER_UNAVAILABLE),
        (b"x", _Stt(""), True, VoiceReasonCode.TEXT_TOO_LARGE),
        (b"x", _Stt("abcdef"), True, VoiceReasonCode.TEXT_TOO_LARGE),
        (b"x", _Stt("ok"), False, VoiceReasonCode.CONSENT_REQUIRED),
    ],
)
def test_voice_transcription_rejects_invalid_inputs_and_provider_outputs(audio, stt, consent, reason) -> None:
    voice = VoiceBoundary(stt=stt, config=VoiceConfig(max_audio_bytes=4, max_text_chars=5))
    with pytest.raises(VoiceBoundaryError, match=reason.value):
        voice.transcribe(audio, locale="en", consent_granted=consent)


def test_voice_transcription_maps_provider_failure_and_preserves_boundary_errors() -> None:
    direct = VoiceBoundaryError(VoiceReasonCode.AUDIO_INVALID.value)
    with pytest.raises(VoiceBoundaryError, match=VoiceReasonCode.AUDIO_INVALID.value):
        VoiceBoundary(stt=_Stt(error=direct)).transcribe(b"x", locale="en", consent_granted=True)

    with pytest.raises(VoiceBoundaryError, match=VoiceReasonCode.PROVIDER_FAILED.value):
        VoiceBoundary(stt=_Stt(error=RuntimeError("private provider detail"))).transcribe(
            b"x", locale="en", consent_granted=True
        )


@pytest.mark.parametrize(
    ("text", "tts", "consent", "reason"),
    [
        ("", _Tts(), True, VoiceReasonCode.TEXT_TOO_LARGE),
        ("abcdef", _Tts(), True, VoiceReasonCode.TEXT_TOO_LARGE),
        ("ok", None, True, VoiceReasonCode.PROVIDER_UNAVAILABLE),
        ("ok", _Tts(b""), True, VoiceReasonCode.PROVIDER_FAILED),
        ("ok", _Tts(b"12345"), True, VoiceReasonCode.SYNTHESIZED_AUDIO_TOO_LARGE),
        ("ok", _Tts(), False, VoiceReasonCode.CONSENT_REQUIRED),
    ],
)
def test_voice_synthesis_rejects_invalid_inputs_and_provider_outputs(text, tts, consent, reason) -> None:
    voice = VoiceBoundary(tts=tts, config=VoiceConfig(max_text_chars=5, max_synthesized_bytes=4))
    with pytest.raises(VoiceBoundaryError, match=reason.value):
        voice.synthesize(text, locale="en", consent_granted=consent)


def test_voice_synthesis_normalizes_text_and_maps_provider_errors() -> None:
    provider = _Tts(b"ok")
    voice = VoiceBoundary(tts=provider)
    assert voice.synthesize("  system   status ", locale="ru", consent_granted=True) == b"ok"
    assert provider.calls == [("system status", "ru")]

    direct = VoiceBoundaryError(VoiceReasonCode.TEXT_TOO_LARGE.value)
    with pytest.raises(VoiceBoundaryError, match=VoiceReasonCode.TEXT_TOO_LARGE.value):
        VoiceBoundary(tts=_Tts(error=direct)).synthesize("ok", locale="en", consent_granted=True)

    with pytest.raises(VoiceBoundaryError, match=VoiceReasonCode.PROVIDER_FAILED.value):
        VoiceBoundary(tts=_Tts(error=RuntimeError("private provider detail"))).synthesize(
            "ok", locale="en", consent_granted=True
        )


@pytest.mark.parametrize(
    ("transcript", "accepted", "reason", "mode"),
    [
        ("", False, VoiceReasonCode.TEXT_TOO_LARGE, None),
        ("attack target", False, VoiceReasonCode.ACTION_GATEWAY_REQUIRED, None),
        ("используй зелье", False, VoiceReasonCode.ACTION_GATEWAY_REQUIRED, None),
        ("unknown command", False, VoiceReasonCode.UNSUPPORTED_COMMAND, None),
        ("okay", True, VoiceReasonCode.ACCEPTED, "ACKNOWLEDGE"),
        ("принято", True, VoiceReasonCode.ACCEPTED, "ACKNOWLEDGE"),
        ("hide", True, VoiceReasonCode.ACCEPTED, "DISMISS"),
        ("скрыть", True, VoiceReasonCode.ACCEPTED, "DISMISS"),
        ("status", True, VoiceReasonCode.ACCEPTED, "OBSERVE"),
        ("покажи", True, VoiceReasonCode.ACCEPTED, "OBSERVE"),
    ],
)
def test_voice_classifier_maps_only_presentation_intents(transcript, accepted, reason, mode) -> None:
    result = VoiceBoundary().classify(transcript, recommendation_id="rec-1", locale="ru")
    assert result.accepted is accepted
    assert result.reason_code is reason
    if mode is None:
        assert result.intent is None
    else:
        assert result.intent is not None
        assert result.intent.mode.value == mode
        assert result.intent.surface.value == "VOICE"
        assert result.intent.locale == "ru"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, True),
        (False, False),
        ("true", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        ("yes", None),
        (1, None),
    ],
)
def test_payload_bool_is_strict_and_noncoercive(value, expected) -> None:
    assert _payload_bool(value) is expected


def test_experience_surfaces_entitlement_failure_as_degraded_warning() -> None:
    runtime = connected_runtime()
    envelope = update_envelope().model_copy(
        update={"payload": {**update_envelope().payload, "account_entitled": "false"}}
    )
    snapshot = runtime.process_update(envelope, session_id="session-1", now=NOW)
    assert snapshot.entitlement is False
    assert snapshot.degraded is True
    assert "ACCOUNT_NOT_ENTITLED" in snapshot.warnings
