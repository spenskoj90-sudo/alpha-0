from __future__ import annotations

"""Bounded Companion runtime composition for the first player experience slice.

This module deliberately composes existing transport, WoW, UGS,
recommendation, presentation, and interaction contracts. It does not open a
socket, call a provider, or execute game actions. Those seams remain explicit
so an integration can be tested without claiming a real WoW 3.3.5a runtime.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .companion_health_api import companion_health_response
from .companion_interaction import (
    CompanionPresentation,
    CompanionPresentationKind,
)
from .companion_presentation import health_presentation, recommendation_presentations
from .companion_protocol import (
    CompanionEnvelope,
    CompanionMessageType,
    CompanionMode,
    LatencyClass,
)
from .companion_transport import CompanionRuntimeHealth, CompanionTransportSession
from .interaction_contract import InteractionIntent, InteractionMode, InteractionSurface
from .models import RecommendationResponse
from .wow_adapter import WowObservation
from .wow_vertical_slice import WowVerticalResult, WowVerticalSlice


class VoiceBoundaryError(RuntimeError):
    """A bounded voice operation was rejected before provider I/O."""


class VoiceReasonCode(StrEnum):
    ACCEPTED = "VOICE_ACCEPTED"
    CONSENT_REQUIRED = "VOICE_CONSENT_REQUIRED"
    AUDIO_TOO_LARGE = "VOICE_AUDIO_TOO_LARGE"
    TEXT_TOO_LARGE = "VOICE_TEXT_TOO_LARGE"
    PROVIDER_UNAVAILABLE = "VOICE_PROVIDER_UNAVAILABLE"
    ACTION_GATEWAY_REQUIRED = "ACTION_GATEWAY_REQUIRED"
    UNSUPPORTED_COMMAND = "VOICE_COMMAND_UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    """Privacy and resource limits applied before any STT/TTS provider call."""

    max_audio_bytes: int = 512_000
    max_text_chars: int = 2_000
    max_synthesized_bytes: int = 2_000_000

    def __post_init__(self) -> None:
        if self.max_audio_bytes <= 0 or self.max_text_chars <= 0 or self.max_synthesized_bytes <= 0:
            raise ValueError("voice limits must be positive")


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio: bytes, *, locale: str) -> str:
        ...


class TextToSpeechProvider(Protocol):
    def synthesize(self, text: str, *, locale: str) -> bytes:
        ...


@dataclass(frozen=True, slots=True)
class VoiceCommandResult:
    accepted: bool
    reason_code: VoiceReasonCode
    intent: InteractionIntent | None
    transcript: str


class VoiceBoundary:
    """Provider-neutral STT/TTS boundary with fail-closed command handling."""

    def __init__(
        self,
        *,
        stt: SpeechToTextProvider | None = None,
        tts: TextToSpeechProvider | None = None,
        config: VoiceConfig | None = None,
    ) -> None:
        self.config = config or VoiceConfig()
        self.stt = stt
        self.tts = tts

    def transcribe(self, audio: bytes, *, locale: str, consent_granted: bool) -> str:
        if not consent_granted:
            raise VoiceBoundaryError(VoiceReasonCode.CONSENT_REQUIRED.value)
        if len(audio) > self.config.max_audio_bytes:
            raise VoiceBoundaryError(VoiceReasonCode.AUDIO_TOO_LARGE.value)
        if self.stt is None:
            raise VoiceBoundaryError(VoiceReasonCode.PROVIDER_UNAVAILABLE.value)
        transcript = self.stt.transcribe(bytes(audio), locale=locale).strip()
        if not transcript or len(transcript) > self.config.max_text_chars:
            raise VoiceBoundaryError(VoiceReasonCode.TEXT_TOO_LARGE.value)
        return transcript

    def synthesize(self, text: str, *, locale: str, consent_granted: bool) -> bytes:
        if not consent_granted:
            raise VoiceBoundaryError(VoiceReasonCode.CONSENT_REQUIRED.value)
        normalized = " ".join(text.split())
        if not normalized or len(normalized) > self.config.max_text_chars:
            raise VoiceBoundaryError(VoiceReasonCode.TEXT_TOO_LARGE.value)
        if self.tts is None:
            raise VoiceBoundaryError(VoiceReasonCode.PROVIDER_UNAVAILABLE.value)
        result = bytes(self.tts.synthesize(normalized, locale=locale))
        if len(result) > self.config.max_synthesized_bytes:
            raise VoiceBoundaryError(VoiceReasonCode.TEXT_TOO_LARGE.value)
        return result

    def classify(self, transcript: str, *, recommendation_id: str, locale: str = "en") -> VoiceCommandResult:
        """Map voice to presentation intents only; action language is rejected."""
        normalized = " ".join(transcript.split()).lower()
        if not normalized or len(normalized) > self.config.max_text_chars:
            return VoiceCommandResult(False, VoiceReasonCode.TEXT_TOO_LARGE, None, transcript)
        action_words = {
            "cast", "attack", "move", "click", "equip", "execute", "use", "атакуй", "выполни", "используй",
        }
        if any(word in normalized.split() for word in action_words):
            return VoiceCommandResult(False, VoiceReasonCode.ACTION_GATEWAY_REQUIRED, None, transcript)
        if normalized in {"ok", "okay", "ack", "acknowledge", "понятно", "принято"}:
            mode = InteractionMode.ACKNOWLEDGE
        elif normalized in {"dismiss", "close", "hide", "отклонить", "скрыть"}:
            mode = InteractionMode.DISMISS
        elif normalized in {"show", "observe", "status", "покажи", "статус"}:
            mode = InteractionMode.OBSERVE
        else:
            return VoiceCommandResult(False, VoiceReasonCode.UNSUPPORTED_COMMAND, None, transcript)
        intent = InteractionIntent(
            surface=InteractionSurface.VOICE,
            mode=mode,
            recommendation_id=recommendation_id,
            locale=locale,
        )
        return VoiceCommandResult(True, VoiceReasonCode.ACCEPTED, intent, transcript)


@dataclass(frozen=True, slots=True)
class CompanionExperienceSnapshot:
    """Complete bounded state presented to Overlay/voice consumers."""

    vertical: WowVerticalResult
    recommendation: RecommendationResponse
    presentations: tuple[CompanionPresentation, ...]
    health: CompanionRuntimeHealth
    entitlement: bool | None
    degraded: bool
    warnings: tuple[str, ...]
    capability_claims: tuple[str, ...]


class CompanionExperienceRuntime:
    """Compose authenticated Companion ingress through the player experience."""

    def __init__(
        self,
        session: CompanionTransportSession,
        *,
        vertical: WowVerticalSlice | None = None,
        voice: VoiceBoundary | None = None,
    ) -> None:
        self.session = session
        self.vertical = vertical or WowVerticalSlice()
        self.voice = voice or VoiceBoundary()
        self._next_outbound_sequence = 0

    def process_update(
        self,
        envelope: CompanionEnvelope,
        *,
        session_id: str,
        now=None,
        provider_id: str | None = None,
    ) -> CompanionExperienceSnapshot:
        health_before = self.session.health()
        if not health_before.peer_authenticated:
            raise PermissionError("PEER_AUTHENTICATION_REQUIRED")
        vertical_result = self.vertical.ingest_companion_envelope(
            envelope,
            session_id=session_id,
            peer_authenticated=True,
            now=now,
        )
        recommendation = self.vertical.recommend(vertical_result, provider_id=provider_id)
        return self._compose_snapshot(
            vertical_result,
            recommendation,
            _payload_bool(envelope.payload.get("account_entitled")),
        )

    def process_observation(
        self,
        observation: WowObservation,
        *,
        session_id: str,
        now=None,
        provider_id: str | None = None,
    ) -> CompanionExperienceSnapshot:
        """Compose a server-validated passive observation into player presentations."""
        health_before = self.session.health()
        if not health_before.peer_authenticated:
            raise PermissionError("PEER_AUTHENTICATION_REQUIRED")
        vertical_result = self.vertical.ingest_observation(
            observation,
            session_id=session_id,
            now=now,
        )
        recommendation = self.vertical.recommend(vertical_result, provider_id=provider_id)
        return self._compose_snapshot(vertical_result, recommendation, observation.account_entitled)

    def _compose_snapshot(
        self,
        vertical_result: WowVerticalResult,
        recommendation: RecommendationResponse,
        entitlement: bool | None,
    ) -> CompanionExperienceSnapshot:
        health = self.session.health()
        warnings: list[str] = []
        if entitlement is False:
            warnings.append("ACCOUNT_NOT_ENTITLED")
        if health.mode is not CompanionMode.ACTIVE:
            warnings.append("COMPANION_DEGRADED")
        presentations = (
            health_presentation(health),
            *recommendation_presentations(recommendation),
        )
        claims = (
            "wow-observation:implemented",
            "wow-addon:passive-telemetry-only",
            "overlay:presentation-runtime",
            "voice:provider-seam-unverified",
            "wow-3.3.5a:external-environment-unverified",
        )
        return CompanionExperienceSnapshot(
            vertical=vertical_result,
            recommendation=recommendation,
            presentations=presentations,
            health=health,
            entitlement=entitlement,
            degraded=bool(warnings),
            warnings=tuple(warnings),
            capability_claims=claims,
        )

    def enqueue_presentations(self, snapshot: CompanionExperienceSnapshot) -> int:
        """Route presentation-only messages through the bounded outbound queue."""
        accepted = 0
        for presentation in snapshot.presentations:
            envelope = CompanionEnvelope(
                sequence=self._next_outbound_sequence,
                message_type=CompanionMessageType.PRESENTATION,
                latency_class=LatencyClass.RESPONSIVE,
                payload={
                    "presentation_id": str(presentation.presentation_id),
                    "correlation_id": str(presentation.correlation_id),
                    "channel": presentation.channel.value,
                    "kind": presentation.kind.value,
                    "text": presentation.text,
                    "confidence": presentation.confidence,
                    "provenance": list(presentation.provenance),
                    "action_capable": presentation.action_capable,
                },
            )
            self._next_outbound_sequence += 1
            accepted += int(self.session.enqueue(envelope))
        return accepted

    @staticmethod
    def health_payload(health: CompanionRuntimeHealth) -> dict[str, object]:
        return companion_health_response(health)


def _payload_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return None
