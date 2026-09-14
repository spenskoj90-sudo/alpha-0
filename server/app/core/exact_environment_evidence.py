from __future__ import annotations

import hashlib
import json
import re
from datetime import timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .game_adapter import (
    AdapterIdentity,
    AdapterRegistry,
    Capability,
    CapabilityChange,
    CapabilityStatus,
    DataQuality,
    EvidenceLevel,
    _issue_l3_capability_admission,
)
from .wow_adapter import ConservativeWowAdapter, WowObservation, WowPatchProfile, WowServerProfile


_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EVIDENCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_REQUIRED_WOW_PROVENANCE = {
    "sentinel-addon-savedvariables",
    "sentinel-launcher-checkpoint",
}
_EXPECTED_HANDSHAKE = {
    "protocol_version": "1.0",
    "ugs_schema_version": "1.0",
    "adapter_contract_version": "1.0",
    "core_protocol_version": "1.0",
    "capability_profile": "wow.passive.v1",
}


class EvidenceExecutionMode(StrEnum):
    LIVE_EXACT_ENVIRONMENT = "live-exact-environment"
    REPLAY = "replay"
    SYNTHETIC = "synthetic"


class PackagedHostProvenance(BaseModel):
    """Build identity embedded inside the packaged Companion application."""

    model_config = ConfigDict(extra="forbid")

    schema: str = Field(pattern=r"^sentinel\.packaged-companion-runtime\.v1$")
    source_sha: str
    target: str = Field(pattern=r"^win32-x64$")
    package_version: str = Field(min_length=1, max_length=64)
    electron_version: str = Field(min_length=1, max_length=32)
    signed: bool
    provenance_file_sha256: str

    @field_validator("source_sha")
    @classmethod
    def validate_source_sha(cls, value: str) -> str:
        if not _GIT_SHA_RE.fullmatch(value):
            raise ValueError("packaged host source_sha must be a lowercase 40-character Git SHA")
        return value

    @field_validator("provenance_file_sha256")
    @classmethod
    def validate_provenance_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("packaged host provenance digest must be lowercase SHA-256")
        return value


class CompanionHandshakeEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted_at: object
    accepted: bool
    mode: str = Field(min_length=1, max_length=32)
    protocol_version: str = Field(min_length=1, max_length=32)
    ugs_schema_version: str = Field(min_length=1, max_length=32)
    adapter_contract_version: str = Field(min_length=1, max_length=32)
    core_protocol_version: str = Field(min_length=1, max_length=32)
    capability_profile: str = Field(min_length=1, max_length=64)

    @field_validator("accepted_at", mode="before")
    @classmethod
    def parse_accepted_at(cls, value: object) -> object:
        from datetime import datetime
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("accepted_at must be an RFC3339 datetime")


class CompanionRuntimeHealthEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    captured_at: object
    connection_id: str = Field(min_length=1, max_length=128)
    mode: str = Field(min_length=1, max_length=32)
    reconnect_attempts: int = Field(ge=0, le=10_000)
    queue_depth: int = Field(ge=0, le=4096)
    dropped_events: int = Field(ge=0, le=1_000_000)
    kill_switch_active: bool
    peer_authenticated: bool
    rtt_ms: float = Field(ge=0, le=60_000)

    @field_validator("captured_at", mode="before")
    @classmethod
    def parse_captured_at(cls, value: object) -> object:
        from datetime import datetime
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("captured_at must be an RFC3339 datetime")


class CoreObservationAckEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    accepted: bool
    reason: str = Field(min_length=1, max_length=128)
    acknowledged_at: object

    @field_validator("acknowledged_at", mode="before")
    @classmethod
    def parse_acknowledged_at(cls, value: object) -> object:
        from datetime import datetime
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("acknowledged_at must be an RFC3339 datetime")


class LiveWowCheckpointEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint_sha256: str
    checkpoint_size_bytes: int = Field(gt=0, le=256 * 1024)
    path_fingerprint_sha256: str
    captured_at: object
    observation: WowObservation
    core_ack: CoreObservationAckEvidence

    @field_validator("checkpoint_sha256", "path_fingerprint_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("checkpoint evidence digests must be lowercase SHA-256")
        return value

    @field_validator("captured_at", mode="before")
    @classmethod
    def parse_captured_at(cls, value: object) -> object:
        from datetime import datetime
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("captured_at must be an RFC3339 datetime")


class ExactEnvironmentEvidenceBundle(BaseModel):
    """Bounded evidence admitted only for a real exact-target WoW run.

    CI/replay can exercise this schema and validator, but must never emit an
    accepted production evidence bundle. The execution_mode distinction is
    deliberate so controlled tests cannot silently become L3 evidence.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    evidence_id: str
    execution_mode: EvidenceExecutionMode
    source_sha: str
    started_at: object
    completed_at: object
    adapter_identity: AdapterIdentity
    packaged_host: PackagedHostProvenance
    handshake: CompanionHandshakeEvidence
    health_samples: list[CompanionRuntimeHealthEvidence] = Field(min_length=1, max_length=64)
    checkpoints: list[LiveWowCheckpointEvidence] = Field(min_length=2, max_length=64)
    capability_claims: list[str] = Field(min_length=1, max_length=16)

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, value: str) -> str:
        if not _EVIDENCE_ID_RE.fullmatch(value):
            raise ValueError("invalid evidence_id")
        return value

    @field_validator("source_sha")
    @classmethod
    def validate_source_sha(cls, value: str) -> str:
        if not _GIT_SHA_RE.fullmatch(value):
            raise ValueError("source_sha must be a lowercase 40-character Git SHA")
        return value

    @field_validator("started_at", "completed_at", mode="before")
    @classmethod
    def parse_run_time(cls, value: object) -> object:
        from datetime import datetime
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("run timestamps must be RFC3339 datetimes")

    @field_validator("capability_claims")
    @classmethod
    def validate_claim_list(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("capability_claims must be unique")
        if any(not item or len(item) > 128 for item in value):
            raise ValueError("capability_claims entries must be non-empty and <=128 characters")
        return value

    @model_validator(mode="after")
    def validate_timeline(self) -> "ExactEnvironmentEvidenceBundle":
        from datetime import datetime
        started_at = self.started_at
        completed_at = self.completed_at
        if not isinstance(started_at, datetime) or not isinstance(completed_at, datetime):
            raise ValueError("run timestamps are invalid")
        if started_at.tzinfo is None or completed_at.tzinfo is None:
            raise ValueError("run timestamps must be timezone-aware")
        if completed_at <= started_at:
            raise ValueError("completed_at must be after started_at")
        if completed_at - started_at > timedelta(hours=8):
            raise ValueError("exact-environment evidence run exceeds eight-hour bound")
        return self


class ExactEnvironmentAdmissionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    evidence_id: str
    source_sha: str
    evidence_digest_sha256: str
    adapter_id: str
    environment_id: str
    capability_names: list[str]
    checkpoint_count: int
    health_sample_count: int


def canonical_evidence_digest(bundle: ExactEnvironmentEvidenceBundle) -> str:
    payload = json.dumps(
        bundle.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_aware(value: object, field_name: str):
    from datetime import datetime
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _validate_identity(bundle: ExactEnvironmentEvidenceBundle) -> tuple[WowPatchProfile, WowServerProfile]:
    identity = bundle.adapter_identity
    adapter = ConservativeWowAdapter
    if identity.adapter_id != adapter.adapter_id:
        raise ValueError("L3 evidence adapter_id does not match conservative WoW adapter")
    if identity.adapter_version != adapter.adapter_version:
        raise ValueError("L3 evidence adapter_version mismatch")
    if identity.game_id != "world-of-warcraft":
        raise ValueError("L3 evidence game_id mismatch")
    if identity.capability_profile_version != adapter.capability_profile_version:
        raise ValueError("L3 evidence capability profile version mismatch")
    if not identity.environment_id:
        raise ValueError("L3 evidence requires an exact environment_id")
    if not identity.client_version:
        raise ValueError("L3 evidence requires an exact client_version")
    if not identity.server_profile:
        raise ValueError("L3 evidence requires an exact server_profile")
    try:
        patch_profile = WowPatchProfile(identity.client_version)
        server_profile = WowServerProfile(identity.server_profile)
    except ValueError as exc:
        raise ValueError("L3 evidence uses an unsupported WoW patch/server profile") from exc
    if server_profile == WowServerProfile.UNKNOWN:
        raise ValueError("L3 evidence cannot use unknown server profile")
    if identity.client_family != patch_profile.value.split("-")[0]:
        raise ValueError("L3 evidence client_family does not match patch profile")
    return patch_profile, server_profile


def _validate_packaged_host(bundle: ExactEnvironmentEvidenceBundle) -> None:
    host = bundle.packaged_host
    if host.source_sha != bundle.source_sha:
        raise ValueError("packaged host source SHA does not match evidence source SHA")
    if not host.package_version:
        raise ValueError("packaged host version is required")


def _validate_handshake(bundle: ExactEnvironmentEvidenceBundle) -> None:
    handshake = bundle.handshake
    accepted_at = _require_aware(handshake.accepted_at, "handshake.accepted_at")
    if not handshake.accepted or handshake.mode != "ACTIVE":
        raise ValueError("L3 evidence requires an accepted ACTIVE Companion handshake")
    for key, expected in _EXPECTED_HANDSHAKE.items():
        if getattr(handshake, key) != expected:
            raise ValueError(f"L3 evidence handshake mismatch: {key}")
    if not bundle.started_at <= accepted_at <= bundle.completed_at:
        raise ValueError("handshake acceptance is outside the evidence run")


def _validate_health(bundle: ExactEnvironmentEvidenceBundle) -> None:
    connection_ids: set[str] = set()
    for sample in bundle.health_samples:
        captured_at = _require_aware(sample.captured_at, "health.captured_at")
        if not bundle.started_at <= captured_at <= bundle.completed_at:
            raise ValueError("runtime health sample is outside the evidence run")
        if sample.mode != "ACTIVE":
            raise ValueError("L3 runtime health must remain ACTIVE")
        if not sample.peer_authenticated:
            raise ValueError("L3 runtime health requires an authenticated Companion peer")
        if sample.kill_switch_active:
            raise ValueError("L3 runtime health cannot be captured with kill switch active")
        connection_ids.add(sample.connection_id)
    if len(connection_ids) != 1:
        raise ValueError("L3 evidence must bind to exactly one Companion connection")


def _validate_checkpoints(
    bundle: ExactEnvironmentEvidenceBundle,
    patch_profile: WowPatchProfile,
    server_profile: WowServerProfile,
) -> list[LiveWowCheckpointEvidence]:
    ordered = sorted(bundle.checkpoints, key=lambda item: item.captured_at)
    event_ids: set[str] = set()
    checkpoint_digests: set[str] = set()
    previous_sequence: int | None = None
    realm_ids: set[str] = set()
    for checkpoint in ordered:
        captured_at = _require_aware(checkpoint.captured_at, "checkpoint.captured_at")
        observed_at = _require_aware(checkpoint.observation.observed_at, "checkpoint.observation.observed_at")
        acknowledged_at = _require_aware(checkpoint.core_ack.acknowledged_at, "checkpoint.core_ack.acknowledged_at")
        if captured_at < bundle.started_at - timedelta(seconds=30) or captured_at > bundle.completed_at:
            raise ValueError("checkpoint capture is outside the evidence run")
        if observed_at < bundle.started_at - timedelta(seconds=30) or observed_at > bundle.completed_at:
            raise ValueError("WoW observation time is outside the evidence run")
        if captured_at + timedelta(seconds=5) < observed_at:
            raise ValueError("checkpoint capture predates its observation")
        if acknowledged_at + timedelta(seconds=5) < captured_at or acknowledged_at > bundle.completed_at + timedelta(seconds=30):
            raise ValueError("Core acknowledgement time is inconsistent with checkpoint capture")

        observation = checkpoint.observation
        ack = checkpoint.core_ack
        if observation.patch_profile != patch_profile or observation.server_profile != server_profile:
            raise ValueError("checkpoint environment does not match exact adapter identity")
        if observation.data_quality == DataQuality.UNKNOWN:
            raise ValueError("L3 checkpoint cannot have UNKNOWN data quality")
        if not _REQUIRED_WOW_PROVENANCE.issubset(set(observation.provenance)):
            raise ValueError("L3 checkpoint is missing launcher/addon provenance")
        if observation.addon_connected is not True:
            raise ValueError("L3 checkpoint requires addon_connected=true")
        if observation.launcher_associated is False or observation.account_entitled is False:
            raise ValueError("L3 checkpoint contains a failed launcher/account association")
        if not ack.accepted or ack.reason != "PASSIVE_CHECKPOINT_ACCEPTED" or ack.event_id != observation.event_id:
            raise ValueError("L3 checkpoint requires a matching accepted Core acknowledgement")
        if observation.event_id in event_ids:
            raise ValueError("L3 checkpoints must have unique event IDs")
        if checkpoint.checkpoint_sha256 in checkpoint_digests:
            raise ValueError("L3 checkpoints must have distinct source digests")
        if previous_sequence is not None and observation.sequence <= previous_sequence:
            raise ValueError("L3 checkpoint sequence must be strictly increasing")
        previous_sequence = observation.sequence
        event_ids.add(observation.event_id)
        checkpoint_digests.add(checkpoint.checkpoint_sha256)
        if observation.realm_id:
            realm_ids.add(observation.realm_id)

    if len(realm_ids) > 1:
        raise ValueError("L3 evidence cannot span multiple realm identities")
    return ordered


def _validate_capability_claims(
    bundle: ExactEnvironmentEvidenceBundle,
    checkpoints: list[LiveWowCheckpointEvidence],
) -> None:
    allowed = set(ConservativeWowAdapter.capability_names())
    unknown = sorted(set(bundle.capability_claims) - allowed)
    if unknown:
        raise ValueError(f"unsupported L3 capability claims: {', '.join(unknown)}")

    observations = [item.observation for item in checkpoints]
    if "wow.realm_profile" in bundle.capability_claims and any(not item.realm_id for item in observations):
        raise ValueError("wow.realm_profile L3 claim requires realm identity in every checkpoint")
    if "wow.latency" in bundle.capability_claims and any(item.latency_ms is None for item in observations):
        raise ValueError("wow.latency L3 claim requires latency in every checkpoint")
    if "wow.addon_status" in bundle.capability_claims and any(item.addon_connected is not True for item in observations):
        raise ValueError("wow.addon_status L3 claim requires addon_connected=true")


def validate_exact_environment_evidence(
    bundle: ExactEnvironmentEvidenceBundle,
) -> ExactEnvironmentAdmissionSummary:
    if bundle.execution_mode != EvidenceExecutionMode.LIVE_EXACT_ENVIRONMENT:
        raise ValueError("L3 admission rejects replay and synthetic execution modes")
    patch_profile, server_profile = _validate_identity(bundle)
    _validate_packaged_host(bundle)
    _validate_handshake(bundle)
    _validate_health(bundle)
    checkpoints = _validate_checkpoints(bundle, patch_profile, server_profile)
    _validate_capability_claims(bundle, checkpoints)
    digest = canonical_evidence_digest(bundle)
    assert bundle.adapter_identity.environment_id is not None
    return ExactEnvironmentAdmissionSummary(
        accepted=True,
        evidence_id=bundle.evidence_id,
        source_sha=bundle.source_sha,
        evidence_digest_sha256=digest,
        adapter_id=bundle.adapter_identity.adapter_id,
        environment_id=bundle.adapter_identity.environment_id,
        capability_names=sorted(bundle.capability_claims),
        checkpoint_count=len(checkpoints),
        health_sample_count=len(bundle.health_samples),
    )


def apply_exact_environment_evidence(
    registry: AdapterRegistry,
    bundle: ExactEnvironmentEvidenceBundle,
) -> tuple[ExactEnvironmentAdmissionSummary, tuple[CapabilityChange | None, ...]]:
    summary = validate_exact_environment_evidence(bundle)
    identity = bundle.adapter_identity
    registered = registry.identity(identity.adapter_id)
    if registered is None:
        registry.register(identity)
    elif registered != identity:
        raise ValueError("registered adapter identity does not match exact-environment evidence")

    changes: list[CapabilityChange | None] = []
    for capability_name in summary.capability_names:
        capability = Capability(
            status=CapabilityStatus.AVAILABLE,
            evidence_level=EvidenceLevel.L3,
            source=[f"exact-env:{summary.evidence_id}", "core-accepted-wow-checkpoint"],
            updated_at=bundle.completed_at,
            constraints=[
                "passive-observation-only",
                "no-action-authorization",
                "exact-environment-bound",
            ],
        )
        admission = _issue_l3_capability_admission(
            adapter_id=identity.adapter_id,
            capability_name=capability_name,
            capability=capability,
            environment_id=summary.environment_id,
            evidence_id=summary.evidence_id,
            evidence_digest_sha256=summary.evidence_digest_sha256,
        )
        changes.append(registry._admit_l3_capability(admission))
    return summary, tuple(changes)
