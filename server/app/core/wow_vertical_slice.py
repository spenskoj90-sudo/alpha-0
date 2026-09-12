from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .companion_protocol import CompanionEnvelope, CompanionMessageType
from .game_adapter import CapabilityStatus
from .recommendation_application import RecommendationApplication
from .recommendation_context import recommendation_context
from .unified_game_state import CapabilitySnapshot, UGSIngestor, UGSState
from .ugs_projection import ProjectionResult, UGSProjectionRegistry
from .wow_adapter import ConservativeWowAdapter, WowObservation, WowPatchProfile, WowServerProfile


@dataclass(frozen=True, slots=True)
class WowVerticalResult:
    """Evidence returned by one deterministic WoW -> UGS -> recommendation pass."""

    accepted: bool
    event_id: str
    session_id: str
    sequence: int
    state: UGSState
    projection: ProjectionResult
    context: Mapping[str, Any]


class WowVerticalSlice:
    """Connect the passive WoW observation boundary to UGS and recommendations.

    The slice is transport-neutral. A Companion envelope may enter only after its
    caller has established the authenticated transport boundary. This class never
    opens sockets, performs TLS, authorizes game actions, or calls an external AI.
    """

    def __init__(
        self,
        *,
        adapter: ConservativeWowAdapter | None = None,
        ingestor: UGSIngestor | None = None,
        projections: UGSProjectionRegistry | None = None,
        recommendations: RecommendationApplication | None = None,
    ) -> None:
        self.adapter = adapter or ConservativeWowAdapter()
        self.ingestor = ingestor or UGSIngestor()
        self.projections = projections or UGSProjectionRegistry()
        self.recommendations = recommendations or RecommendationApplication()
        self._projected_context: dict[str, Mapping[str, Any]] = {}
        if "recommendation-context" not in self.projections.names():
            self.projections.register("recommendation-context", self._project_context)

    def ingest_observation(
        self,
        observation: WowObservation,
        *,
        session_id: str,
        now: datetime | None = None,
    ) -> WowVerticalResult:
        if not session_id or len(session_id) > 128:
            raise ValueError("session_id must be non-empty and <=128 characters")
        ingested_at = now or datetime.now(timezone.utc)
        if ingested_at.tzinfo is None:
            raise ValueError("now must include timezone information")

        event = self.adapter.normalize(observation)
        identity = self.adapter.identity(
            patch_profile=observation.patch_profile,
            server_profile=observation.server_profile,
        )
        capabilities = {
            name: CapabilitySnapshot(
                status=capability.status,
                evidence_level=capability.evidence_level,
            )
            for name, capability in self.adapter.capabilities(observed_at=observation.observed_at).items()
        }
        state = UGSState(
            schema_version="1.0",
            state_id=f"wow:{observation.event_id}",
            session_id=session_id,
            sequence=observation.sequence,
            observed_at=observation.observed_at,
            ingested_at=ingested_at,
            source=identity_source(identity.adapter_id, identity.server_profile or WowServerProfile.UNKNOWN.value),
            capabilities=capabilities,
            events=[event],
            data_quality=observation.data_quality,
            missing_signals=[],
            provenance=list(observation.provenance) or [self.adapter.adapter_id],
        )
        accepted = self.ingestor.accept(state)
        if not accepted:
            raise ValueError("UGS_SEQUENCE_REPLAY")
        projection = self.projections.apply(state)
        context = recommendation_context(state)
        return WowVerticalResult(
            accepted=True,
            event_id=observation.event_id,
            session_id=session_id,
            sequence=observation.sequence,
            state=state,
            projection=projection,
            context=context,
        )

    def recommend(self, result: WowVerticalResult, *, provider_id: str | None = None):
        """Generate the bounded provider-neutral recommendation for this state."""
        return self.recommendations.recommend(result.context, provider_id=provider_id)

    def ingest_companion_envelope(
        self,
        envelope: CompanionEnvelope,
        *,
        session_id: str,
        peer_authenticated: bool,
        now: datetime | None = None,
    ) -> WowVerticalResult:
        """Accept only authenticated Companion UGS_UPDATE envelopes."""
        if not peer_authenticated:
            raise PermissionError("PEER_AUTHENTICATION_REQUIRED")
        if envelope.message_type != CompanionMessageType.UGS_UPDATE:
            raise ValueError("COMPANION_MESSAGE_NOT_UGS_UPDATE")
        payload = envelope.payload
        observation = WowObservation(
            event_id=str(payload.get("event_id", envelope.message_id)),
            observed_at=_parse_timestamp(payload.get("observed_at"), now),
            sequence=envelope.sequence,
            patch_profile=WowPatchProfile(str(payload["patch_profile"])),
            server_profile=WowServerProfile(str(payload.get("server_profile", WowServerProfile.UNKNOWN.value))),
            realm_id=_optional_text(payload.get("realm_id")),
            latency_ms=_optional_int(payload.get("latency_ms")),
            addon_connected=_optional_bool(payload.get("addon_connected")),
            launcher_associated=_optional_bool(payload.get("launcher_associated")),
            account_entitled=_optional_bool(payload.get("account_entitled")),
            combat_state=_optional_text(payload.get("combat_state")),
            provenance=["companion.transport", "wow-addon"],
        )
        return self.ingest_observation(observation, session_id=session_id, now=now)

    def _project_context(self, state: UGSState) -> None:
        self._projected_context[state.session_id] = recommendation_context(state)


def identity_source(adapter_id: str, profile: str):
    from .unified_game_state import SourceIdentity

    return SourceIdentity(adapter_id=adapter_id, profile=profile)


def _parse_timestamp(value: object, fallback: datetime | None) -> datetime:
    if value is None:
        if fallback is None:
            raise ValueError("observed_at is required")
        return fallback
    if not isinstance(value, str):
        raise ValueError("observed_at must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include timezone information")
    return parsed


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("text payload fields must be strings")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("integer payload field is invalid") from exc


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError("boolean payload field is invalid")
