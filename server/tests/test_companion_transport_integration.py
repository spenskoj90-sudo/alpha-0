from datetime import UTC, datetime, timedelta

from app.core.companion_compatibility import negotiate_companion_compatibility
from app.core.companion_observability import BoundedCompanionTelemetrySink
from app.core.companion_peer_auth import AllowlistPeerAuthenticator, PeerAuthEvidence
from app.core.companion_protocol import CompanionEnvelope, CompanionMessageType, LatencyClass
from app.core.companion_runtime import CompanionRuntime
from app.core.companion_transport import CompanionTransportSession


def _envelope() -> CompanionEnvelope:
    return CompanionEnvelope(
        sequence=1,
        message_type=CompanionMessageType.HEALTH,
        latency_class=LatencyClass.RESPONSIVE,
    )


def test_transport_session_emits_bounded_lifecycle_telemetry() -> None:
    sink = BoundedCompanionTelemetrySink(max_events=16)
    runtime = CompanionRuntime(telemetry=sink)
    session = CompanionTransportSession(
        runtime,
        peer_authenticator=AllowlistPeerAuthenticator({"peer-1"}),
    )

    session.connect(
        datetime(2026, 9, 11, tzinfo=UTC),
        auth_evidence=PeerAuthEvidence("test", "peer-1", True),
    )
    assert session.enqueue(_envelope()) is True
    session.mark_send_success(datetime(2026, 9, 11, 0, 0, 0, 1_000, tzinfo=UTC))
    session.mark_transport_failure()

    names = [event.name for event in sink.snapshot()]
    assert "companion.transport.connected" in names
    assert "companion.transport.send.success" in names
    assert "companion.transport.failure" in names
    assert all(event.name.startswith("companion.") for event in sink.snapshot())


def test_transport_session_fail_closed_peer_auth_has_no_active_runtime() -> None:
    sink = BoundedCompanionTelemetrySink(max_events=8)
    runtime = CompanionRuntime(telemetry=sink)
    session = CompanionTransportSession(
        runtime,
        peer_authenticator=AllowlistPeerAuthenticator({"allowed"}),
    )

    try:
        session.connect(auth_evidence=PeerAuthEvidence("test", "denied", True))
    except PermissionError as exc:
        assert str(exc) == "PEER_NOT_ALLOWED"
    else:
        raise AssertionError("unauthorized peer was accepted")

    assert runtime.mode.value == "STOPPED"
    assert session.health().peer_authenticated is False


def test_compatibility_selects_highest_compatible_minor_versions() -> None:
    result = negotiate_companion_compatibility(
        offered_protocol="1.3",
        supported_protocols=("1.0", "1.2"),
        offered_ugs_schema="1.4",
        supported_ugs_schemas=("1.0", "1.3"),
        offered_adapter_contract="1.2",
        supported_adapter_contracts=("1.0", "1.1"),
        offered_core_protocol="1.5",
        supported_core_protocols=("1.0", "1.4"),
        offered_capability_profile="wow.passive.v1",
        supported_capability_profiles=("wow.passive.v1",),
    )

    assert result.accepted is True
    assert result.protocol_version == "1.2"
    assert result.ugs_schema_version == "1.3"
    assert result.adapter_contract_version == "1.1"
    assert result.core_protocol_version == "1.4"


def test_latency_observation_is_real_timestamp_difference() -> None:
    runtime = CompanionRuntime()
    sent = datetime(2026, 9, 11, tzinfo=UTC)
    received = sent + timedelta(milliseconds=37)

    assert runtime.observe_latency(sent, received) == 37.0
    assert runtime.last_latency_ms == 37.0
