from datetime import UTC, datetime, timedelta

import pytest

from app.core.exact_environment_evidence import (
    CompanionHandshakeEvidence,
    CompanionRuntimeHealthEvidence,
    CoreObservationAckEvidence,
    EvidenceExecutionMode,
    ExactEnvironmentEvidenceBundle,
    LiveWowCheckpointEvidence,
    PackagedHostProvenance,
    apply_exact_environment_evidence,
    canonical_evidence_digest,
    validate_exact_environment_evidence,
)
from app.core.game_adapter import AdapterRegistry, CapabilityStatus, DataQuality, EvidenceLevel
from app.core.wow_adapter import ConservativeWowAdapter, WowObservation, WowPatchProfile, WowServerProfile


NOW = datetime(2026, 9, 14, 9, 30, tzinfo=UTC)
SOURCE_SHA = "a" * 40
CONNECTION_ID = "11111111-1111-4111-8111-111111111111"
ENVIRONMENT_ID = "wotlk-335a-private-lab-a"
PROVENANCE = ["sentinel-addon-savedvariables", "sentinel-launcher-checkpoint"]


def checkpoint(sequence: int, offset_seconds: int, digest_char: str, *, realm_id: str = "realm-lab", latency_ms: int | None = 42) -> LiveWowCheckpointEvidence:
    observed_at = NOW + timedelta(seconds=offset_seconds)
    captured_at = observed_at + timedelta(seconds=1)
    event_id = f"wow-checkpoint-{sequence}"
    return LiveWowCheckpointEvidence(
        checkpoint_sha256=digest_char * 64,
        checkpoint_size_bytes=2048 + sequence,
        path_fingerprint_sha256="f" * 64,
        captured_at=captured_at,
        observation=WowObservation(
            event_id=event_id,
            observed_at=observed_at,
            sequence=sequence,
            patch_profile=WowPatchProfile.WOTLK_3_3_5A,
            server_profile=WowServerProfile.PRIVATE,
            realm_id=realm_id,
            latency_ms=latency_ms,
            addon_connected=True,
            launcher_associated=True,
            account_entitled=True,
            combat_state="IDLE",
            data_quality=DataQuality.LOW,
            provenance=PROVENANCE,
        ),
        core_ack=CoreObservationAckEvidence(
            event_id=event_id,
            accepted=True,
            reason="PASSIVE_CHECKPOINT_ACCEPTED",
            acknowledged_at=captured_at + timedelta(seconds=1),
        ),
    )


def valid_bundle() -> ExactEnvironmentEvidenceBundle:
    identity = ConservativeWowAdapter().identity(
        patch_profile=WowPatchProfile.WOTLK_3_3_5A,
        server_profile=WowServerProfile.PRIVATE,
        environment_id=ENVIRONMENT_ID,
    )
    return ExactEnvironmentEvidenceBundle(
        schema_version="1.0",
        evidence_id="l3-wotlk-private-001",
        execution_mode=EvidenceExecutionMode.LIVE_EXACT_ENVIRONMENT,
        source_sha=SOURCE_SHA,
        started_at=NOW,
        completed_at=NOW + timedelta(minutes=3),
        adapter_identity=identity,
        packaged_host=PackagedHostProvenance(
            schema="sentinel.packaged-companion-runtime.v1",
            source_sha=SOURCE_SHA,
            target="win32-x64",
            package_version="0.2.0",
            electron_version="37.2.0",
            signed=False,
            provenance_file_sha256="e" * 64,
        ),
        handshake=CompanionHandshakeEvidence(
            accepted_at=NOW + timedelta(seconds=2),
            accepted=True,
            mode="ACTIVE",
            protocol_version="1.0",
            ugs_schema_version="1.0",
            adapter_contract_version="1.0",
            core_protocol_version="1.0",
            capability_profile="wow.passive.v1",
        ),
        health_samples=[
            CompanionRuntimeHealthEvidence(
                captured_at=NOW + timedelta(seconds=5),
                connection_id=CONNECTION_ID,
                mode="ACTIVE",
                reconnect_attempts=0,
                queue_depth=0,
                dropped_events=0,
                kill_switch_active=False,
                peer_authenticated=True,
                rtt_ms=7.5,
            ),
            CompanionRuntimeHealthEvidence(
                captured_at=NOW + timedelta(seconds=75),
                connection_id=CONNECTION_ID,
                mode="ACTIVE",
                reconnect_attempts=0,
                queue_depth=0,
                dropped_events=0,
                kill_switch_active=False,
                peer_authenticated=True,
                rtt_ms=8.0,
            ),
        ],
        checkpoints=[
            checkpoint(10, 30, "b"),
            checkpoint(11, 60, "c"),
        ],
        capability_claims=list(ConservativeWowAdapter.capability_names()),
    )


def test_valid_live_exact_environment_bundle_is_admitted() -> None:
    bundle = valid_bundle()

    summary = validate_exact_environment_evidence(bundle)

    assert summary.accepted is True
    assert summary.source_sha == SOURCE_SHA
    assert summary.environment_id == ENVIRONMENT_ID
    assert summary.checkpoint_count == 2
    assert summary.health_sample_count == 2
    assert summary.evidence_digest_sha256 == canonical_evidence_digest(bundle)
    assert summary.capability_names == sorted(ConservativeWowAdapter.capability_names())


def test_valid_bundle_is_only_path_to_available_l3_capabilities() -> None:
    registry = AdapterRegistry()

    summary, changes = apply_exact_environment_evidence(registry, valid_bundle())

    assert summary.accepted
    assert len(changes) == len(ConservativeWowAdapter.capability_names())
    for capability_name in ConservativeWowAdapter.capability_names():
        capability = registry.require_usable(ConservativeWowAdapter.adapter_id, capability_name)
        assert capability.status == CapabilityStatus.AVAILABLE
        assert capability.evidence_level == EvidenceLevel.L3
        assert f"exact-env:{summary.evidence_id}" in capability.source
        assert "exact-environment-bound" in capability.constraints


def test_replay_and_synthetic_modes_cannot_become_l3() -> None:
    for mode in (EvidenceExecutionMode.REPLAY, EvidenceExecutionMode.SYNTHETIC):
        bundle = valid_bundle().model_copy(update={"execution_mode": mode})
        with pytest.raises(ValueError, match="rejects replay and synthetic"):
            validate_exact_environment_evidence(bundle)


def test_unknown_server_profile_cannot_be_l3() -> None:
    bundle = valid_bundle()
    identity = ConservativeWowAdapter().identity(
        patch_profile=WowPatchProfile.WOTLK_3_3_5A,
        server_profile=WowServerProfile.UNKNOWN,
        environment_id=ENVIRONMENT_ID,
    )
    bundle = bundle.model_copy(update={"adapter_identity": identity})

    with pytest.raises(ValueError, match="unknown server profile"):
        validate_exact_environment_evidence(bundle)


def test_packaged_host_must_match_exact_source_sha() -> None:
    bundle = valid_bundle()
    host = bundle.packaged_host.model_copy(update={"source_sha": "d" * 40})
    bundle = bundle.model_copy(update={"packaged_host": host})

    with pytest.raises(ValueError, match="source SHA does not match"):
        validate_exact_environment_evidence(bundle)


def test_handshake_must_be_active_and_contract_exact() -> None:
    bundle = valid_bundle()
    handshake = bundle.handshake.model_copy(update={"capability_profile": "wow.other.v1"})
    bundle = bundle.model_copy(update={"handshake": handshake})

    with pytest.raises(ValueError, match="handshake mismatch"):
        validate_exact_environment_evidence(bundle)


def test_health_must_remain_authenticated_active_and_single_connection() -> None:
    bundle = valid_bundle()
    bad = bundle.health_samples[1].model_copy(update={"connection_id": "22222222-2222-4222-8222-222222222222"})
    bundle = bundle.model_copy(update={"health_samples": [bundle.health_samples[0], bad]})

    with pytest.raises(ValueError, match="exactly one Companion connection"):
        validate_exact_environment_evidence(bundle)

    bundle = valid_bundle()
    bad = bundle.health_samples[0].model_copy(update={"peer_authenticated": False})
    bundle = bundle.model_copy(update={"health_samples": [bad]})
    with pytest.raises(ValueError, match="authenticated Companion peer"):
        validate_exact_environment_evidence(bundle)


def test_checkpoint_requires_matching_accepted_core_ack() -> None:
    bundle = valid_bundle()
    first = bundle.checkpoints[0]
    rejected = first.core_ack.model_copy(update={"accepted": False, "reason": "INVALID_WOW_OBSERVATION"})
    first = first.model_copy(update={"core_ack": rejected})
    bundle = bundle.model_copy(update={"checkpoints": [first, bundle.checkpoints[1]]})

    with pytest.raises(ValueError, match="matching accepted Core acknowledgement"):
        validate_exact_environment_evidence(bundle)


def test_checkpoint_requires_live_launcher_and_addon_provenance() -> None:
    bundle = valid_bundle()
    first = bundle.checkpoints[0]
    observation = first.observation.model_copy(update={"provenance": ["sentinel-launcher-checkpoint"]})
    first = first.model_copy(update={"observation": observation})
    bundle = bundle.model_copy(update={"checkpoints": [first, bundle.checkpoints[1]]})

    with pytest.raises(ValueError, match="missing launcher/addon provenance"):
        validate_exact_environment_evidence(bundle)


def test_checkpoint_sequence_and_source_digest_must_advance() -> None:
    bundle = valid_bundle()
    duplicate = checkpoint(10, 60, "b")
    bundle = bundle.model_copy(update={"checkpoints": [bundle.checkpoints[0], duplicate]})

    with pytest.raises(ValueError, match="distinct source digests|strictly increasing"):
        validate_exact_environment_evidence(bundle)


def test_bundle_cannot_span_multiple_realms() -> None:
    bundle = valid_bundle()
    second = checkpoint(11, 60, "c", realm_id="other-realm")
    bundle = bundle.model_copy(update={"checkpoints": [bundle.checkpoints[0], second]})

    with pytest.raises(ValueError, match="multiple realm identities"):
        validate_exact_environment_evidence(bundle)


def test_latency_claim_requires_latency_in_every_checkpoint() -> None:
    bundle = valid_bundle()
    second = checkpoint(11, 60, "c", latency_ms=None)
    bundle = bundle.model_copy(update={"checkpoints": [bundle.checkpoints[0], second]})

    with pytest.raises(ValueError, match="wow.latency"):
        validate_exact_environment_evidence(bundle)


def test_unknown_capability_claim_is_rejected() -> None:
    bundle = valid_bundle().model_copy(update={"capability_claims": ["wow.identity", "wow.memory_write"]})

    with pytest.raises(ValueError, match="unsupported L3 capability"):
        validate_exact_environment_evidence(bundle)


def test_registered_identity_must_match_bundle_exactly() -> None:
    registry = AdapterRegistry()
    other = ConservativeWowAdapter().identity(
        patch_profile=WowPatchProfile.WOTLK_3_3_5A,
        server_profile=WowServerProfile.PRIVATE,
        environment_id="different-environment",
    )
    registry.register(other)

    with pytest.raises(ValueError, match="registered adapter identity"):
        apply_exact_environment_evidence(registry, valid_bundle())
