from datetime import UTC, datetime

import pytest

from app.core.companion_protocol import CompanionEnvelope, CompanionMessageType, LatencyClass
from app.core.wow_adapter import WowObservation, WowPatchProfile, WowServerProfile
from app.core.wow_vertical_slice import WowVerticalSlice


NOW = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)


def observation(sequence: int = 1) -> WowObservation:
    return WowObservation(
        event_id=f"wow-event-{sequence}",
        observed_at=NOW,
        sequence=sequence,
        patch_profile=WowPatchProfile.WOTLK_3_3_5A,
        server_profile=WowServerProfile.PRIVATE,
        realm_id="sentinel-realm",
        latency_ms=42,
        addon_connected=True,
        combat_state="IN_COMBAT",
        provenance=["wow-addon:test"],
    )


def test_wow_observation_reaches_ugs_projection_and_recommendation() -> None:
    vertical = WowVerticalSlice()

    result = vertical.ingest_observation(observation(), session_id="session-1", now=NOW)
    recommendation = vertical.recommend(result)

    assert result.accepted is True
    assert result.state.sequence == 1
    assert result.state.source.adapter_id == "wow-conservative"
    assert result.state.source.profile == "private"
    assert result.state.events[0].event_type == "wow.passive_observation"
    assert result.projection.applied == ("recommendation-context",)
    assert result.context["source"]["profile"] == "private"
    assert "payload" not in result.context
    assert recommendation.recommendations
    assert recommendation.recommendations[0].provider_id == "sentinel-core"


def test_wow_vertical_slice_rejects_sequence_replay() -> None:
    vertical = WowVerticalSlice()
    vertical.ingest_observation(observation(1), session_id="session-1", now=NOW)

    with pytest.raises(ValueError, match="UGS_SEQUENCE_REPLAY"):
        vertical.ingest_observation(observation(1), session_id="session-1", now=NOW)


def test_authenticated_companion_envelope_enters_same_core_boundary() -> None:
    vertical = WowVerticalSlice()
    envelope = CompanionEnvelope(
        sequence=7,
        message_type=CompanionMessageType.UGS_UPDATE,
        latency_class=LatencyClass.RESPONSIVE,
        payload={
            "event_id": "companion-wow-7",
            "observed_at": NOW.isoformat(),
            "patch_profile": "wotlk-3.3.5a",
            "server_profile": "private",
            "realm_id": "realm-7",
            "latency_ms": "55",
            "addon_connected": "true",
        },
    )

    result = vertical.ingest_companion_envelope(
        envelope,
        session_id="companion-session",
        peer_authenticated=True,
        now=NOW,
    )

    assert result.accepted is True
    assert result.event_id == "companion-wow-7"
    assert result.sequence == 7
    assert result.state.events[0].payload["realm_id"] == "realm-7"


def test_companion_ingress_requires_authenticated_peer() -> None:
    vertical = WowVerticalSlice()
    envelope = CompanionEnvelope(
        sequence=1,
        message_type=CompanionMessageType.UGS_UPDATE,
        latency_class=LatencyClass.RESPONSIVE,
        payload={"patch_profile": "wotlk-3.3.5a"},
    )

    with pytest.raises(PermissionError, match="PEER_AUTHENTICATION_REQUIRED"):
        vertical.ingest_companion_envelope(
            envelope,
            session_id="session-1",
            peer_authenticated=False,
            now=NOW,
        )


def test_companion_ingress_rejects_non_ugs_messages() -> None:
    vertical = WowVerticalSlice()
    envelope = CompanionEnvelope(
        sequence=1,
        message_type=CompanionMessageType.HEARTBEAT,
        latency_class=LatencyClass.RESPONSIVE,
    )

    with pytest.raises(ValueError, match="COMPANION_MESSAGE_NOT_UGS_UPDATE"):
        vertical.ingest_companion_envelope(
            envelope,
            session_id="session-1",
            peer_authenticated=True,
            now=NOW,
        )
