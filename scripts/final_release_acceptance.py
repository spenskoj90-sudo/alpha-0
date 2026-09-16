#!/usr/bin/env python3
"""Fail-closed binding for final physical/environment release acceptance.

The active v1 contract requires structured checkpoint completion in addition to retained evidence.
The verifier proves consistency, exact-byte/source binding, and checklist completeness.
It still does not prove that a human actually performed a physical test; the retained
 evidence and Owner-authorized workflow preserve that separate real-world claim.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import release_lineage

SCHEMA = "sentinel.final-release-acceptance.v1"
GATE_SCHEMA = "sentinel.final-release-gate.v1"
CHECKPOINT_SCHEMA = "sentinel.final-release-checkpoints.v1"
PROFILES = ("publication", "deployment", "production-traffic")
PROFILE_RANK = {name: index for index, name in enumerate(PROFILES)}

PUBLICATION_GATES = {
    "android-physical",
    "companion-host",
    "wow-exact-environment",
    "voice-acoustic",
    "accessibility-visual",
}
DEPLOYMENT_GATES = PUBLICATION_GATES | {
    "payment-provider-network",
    "voice-provider-network",
    "runtime-observability-provider",
    "production-database-recovery",
    "production-ingress-readiness",
}
PRODUCTION_TRAFFIC_GATES = DEPLOYMENT_GATES | {"runtime-security-penetration"}
REQUIRED_GATES = {
    "publication": PUBLICATION_GATES,
    "deployment": DEPLOYMENT_GATES,
    "production-traffic": PRODUCTION_TRAFFIC_GATES,
}
OPTIONAL_GATES = {"firebase-test-lab"}
ALL_GATES = PRODUCTION_TRAFFIC_GATES | OPTIONAL_GATES

REQUIRED_CHECKPOINTS: dict[str, tuple[str, ...]] = {
    "android-physical": (
        "install_launch_upgrade",
        "login_refresh_device_proof",
        "background_foreground_process_recreation",
        "network_loss_recovery_bounded_errors",
        "battery_background_constraints",
        "dashboard_device_game_navigation",
        "quality_report_with_without_diagnostics",
        "talkback_traversal_semantics_announcements",
        "text_scaling_orientation_configuration",
        "no_test_build_permission_security_bypass",
    ),
    "companion-host": (
        "packaged_unpack_start",
        "source_version_identity",
        "authenticated_active_health",
        "reconnect_core_unavailable_recovery",
        "kill_switch_fail_closed_authorization",
        "launcher_game_configuration",
        "overlay_focus_clickthrough_multimonitor_dpi",
        "shutdown_restart_sleep_resume",
        "evidence_excludes_credentials_auth_material",
    ),
    "wow-exact-environment": (
        "source_bound_packaged_companion",
        "authenticated_active_handshake",
        "active_runtime_health",
        "persisted_checkpoint_pair",
        "core_passive_checkpoint_ack",
        "l3_bundle_validator_pass",
    ),
    "voice-acoustic": (
        "real_microphone_driver_path",
        "input_selection_permission",
        "capture_start_stop_restart",
        "silence_speech_noise_device_switching",
        "bounded_latency_failure_presentation",
        "device_driver_interruption_recovery",
        "privacy_indicators_explicit_capture_state",
        "no_unintended_background_recording",
    ),
    "accessibility-visual": (
        "android_talkback_traversal",
        "android_names_roles_states",
        "android_validation_error_announcements",
        "android_focus_restoration",
        "android_large_text_contrast_visibility",
        "windows_keyboard_operation",
        "windows_screen_reader_focus_reading",
        "windows_visible_focus_state",
        "windows_overlay_focus_clickthrough",
        "windows_scaling_dpi_multimonitor",
    ),
    "payment-provider-network": (
        "sandbox_or_target_provider_config_bound",
        "provider_authentication_transport",
        "signed_webhook_verified",
        "webhook_idempotent_replay",
        "subscription_lifecycle_transition",
        "provider_failure_recovery",
    ),
    "voice-provider-network": (
        "provider_https_authentication",
        "stt_roundtrip",
        "tts_roundtrip",
        "timeout_retry_recovery",
        "privacy_payload_bounds",
    ),
    "runtime-observability-provider": (
        "exact_release_identity",
        "operational_event_delivery",
        "pii_redaction",
        "provider_failure_isolation",
    ),
    "production-database-recovery": (
        "encrypted_database_connectivity",
        "backup_completed",
        "restore_completed",
        "restored_data_validation",
        "application_reconnect",
    ),
    "production-ingress-readiness": (
        "tls_hostname_validation",
        "trusted_proxy_boundary",
        "security_headers",
        "request_body_limits",
        "health_routing",
    ),
    "runtime-security-penetration": (
        "authentication_authorization",
        "session_device_binding",
        "request_rate_limits",
        "injection_transport_security",
        "secrets_privacy",
        "findings_disposition",
    ),
    "firebase-test-lab": ("external_run_pass",),
}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ENVIRONMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
EXECUTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/+()@-]{0,127}$")
MEDIA_TYPES = {
    "application/json",
    "application/zip",
    "application/pdf",
    "text/plain",
    "image/png",
    "image/jpeg",
    "video/mp4",
}
MAX_JSON_BYTES = 256 * 1024
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _canonical_digest(document: dict[str, Any], digest_field: str) -> str:
    value = copy.deepcopy(document)
    value.pop(digest_field, None)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256(encoded)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    data = path.read_bytes()
    if not data or len(data) > MAX_JSON_BYTES:
        raise ValueError(f"invalid {label} size")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    return _mapping(value, label)


def _normalize_digest(value: str, label: str) -> str:
    normalized = value.strip().lower()
    if not DIGEST_RE.fullmatch(normalized):
        raise ValueError(f"invalid {label} digest")
    return normalized


def _normalize_raw_sha256(value: str, label: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        return _normalize_digest(normalized, label)
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError(f"invalid {label} SHA-256")
    return "sha256:" + normalized


def _read_companion_digest(path: Path) -> str:
    if path.is_symlink():
        raise ValueError("Companion digest file must not be a symlink")
    text_value = path.read_text(encoding="utf-8")
    if len(text_value) > 256:
        raise ValueError("Companion digest file is too large")
    return _normalize_raw_sha256(text_value, "Companion archive")


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("recordedAt must be UTC ISO-8601 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("recordedAt is not valid ISO-8601") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("recordedAt must be UTC")
    return value


def _validate_execution(value: Any, label: str) -> dict[str, str]:
    execution = _mapping(value, label)
    if set(execution) != {"deviceOrHost", "platform", "tool"}:
        raise ValueError(f"{label} has unexpected fields")
    normalized: dict[str, str] = {}
    for key in ("deviceOrHost", "platform", "tool"):
        item = execution.get(key)
        if not isinstance(item, str) or not EXECUTION_RE.fullmatch(item):
            raise ValueError(f"{label} {key} is invalid")
        normalized[key] = item
    return normalized


def _candidate_binding(candidate: dict[str, Any], apk: bytes) -> tuple[dict[str, str], dict[str, str]]:
    release_lineage.verify_candidate_manifest(candidate, apk)
    source = _mapping(candidate.get("source"), "candidate source")
    repository = source.get("repository")
    sha = source.get("sha")
    version = source.get("version")
    if not isinstance(repository, str) or not REPO_RE.fullmatch(repository):
        raise ValueError("invalid candidate repository")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("invalid candidate source SHA")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("invalid candidate version")
    candidate_digest = _normalize_digest(str(candidate.get("candidateDigest", "")), "candidate")
    artifact = _mapping(candidate.get("artifact"), "candidate artifact")
    apk_digest = _normalize_digest(str(artifact.get("sha256", "")), "candidate APK")
    if apk_digest != _sha256(apk):
        raise ValueError("candidate APK digest does not match APK bytes")
    return (
        {"repository": repository, "sha": sha, "version": version},
        {"candidateDigest": candidate_digest, "androidApkSha256": apk_digest},
    )


def _release_binding(candidate: dict[str, Any], apk: bytes, companion_archive_sha256: str) -> tuple[dict[str, str], dict[str, str]]:
    source, candidate_binding = _candidate_binding(candidate, apk)
    return source, {
        **candidate_binding,
        "companionArchiveSha256": _normalize_raw_sha256(companion_archive_sha256, "Companion archive"),
    }


def build_checkpoint_template(
    gate_id: str,
    candidate: dict[str, Any],
    apk: bytes,
    companion_archive_sha256: str,
    environment_id: str,
    execution: dict[str, str],
) -> dict[str, Any]:
    if gate_id not in ALL_GATES:
        raise ValueError("unknown final-acceptance gate")
    if not ENVIRONMENT_RE.fullmatch(environment_id):
        raise ValueError("environmentId must be a bounded opaque identifier")
    source, binding = _release_binding(candidate, apk, companion_archive_sha256)
    normalized_execution = _validate_execution(execution, "checkpoint execution")
    document: dict[str, Any] = {
        "schema": CHECKPOINT_SCHEMA,
        "gateId": gate_id,
        "source": source,
        "binding": binding,
        "environmentId": environment_id,
        "execution": normalized_execution,
        "checkpoints": [{"id": checkpoint_id, "status": "PENDING"} for checkpoint_id in REQUIRED_CHECKPOINTS[gate_id]],
    }
    document["checkpointsDigest"] = _canonical_digest(document, "checkpointsDigest")
    return document


def verify_checkpoints(
    document: dict[str, Any],
    *,
    gate_id: str,
    expected_source: dict[str, str],
    expected_binding: dict[str, str],
    expected_environment_id: str,
    require_pass: bool,
    verify_digest: bool = True,
) -> tuple[dict[str, str], list[dict[str, str]], str]:
    if set(document) != {
        "schema",
        "gateId",
        "source",
        "binding",
        "environmentId",
        "execution",
        "checkpoints",
        "checkpointsDigest",
    }:
        raise ValueError("checkpoint document has unexpected fields")
    if document.get("schema") != CHECKPOINT_SCHEMA or document.get("gateId") != gate_id:
        raise ValueError("checkpoint schema/gate mismatch")
    if document.get("source") != expected_source or document.get("binding") != expected_binding:
        raise ValueError("checkpoint release-byte binding mismatch")
    if document.get("environmentId") != expected_environment_id:
        raise ValueError("checkpoint environment mismatch")
    execution = _validate_execution(document.get("execution"), "checkpoint execution")

    values = document.get("checkpoints")
    if not isinstance(values, list) or not values:
        raise ValueError("checkpoints must be a non-empty list")
    checkpoints: list[dict[str, str]] = []
    ids: list[str] = []
    for raw in values:
        item = _mapping(raw, "checkpoint")
        if set(item) != {"id", "status"}:
            raise ValueError("checkpoint has unexpected fields")
        checkpoint_id = item.get("id")
        status = item.get("status")
        if not isinstance(checkpoint_id, str) or not checkpoint_id:
            raise ValueError("checkpoint id is invalid")
        if status not in {"PENDING", "PASS"}:
            raise ValueError(f"{checkpoint_id} checkpoint status is invalid")
        ids.append(checkpoint_id)
        checkpoints.append({"id": checkpoint_id, "status": status})
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate checkpoint id")
    required = set(REQUIRED_CHECKPOINTS[gate_id])
    actual = set(ids)
    if actual != required:
        missing = sorted(required - actual)
        unknown = sorted(actual - required)
        parts = []
        if missing:
            parts.append("missing=" + ",".join(missing))
        if unknown:
            parts.append("unknown=" + ",".join(unknown))
        raise ValueError("checkpoint set mismatch: " + ";".join(parts))
    if require_pass:
        incomplete = sorted(item["id"] for item in checkpoints if item["status"] != "PASS")
        if incomplete:
            raise ValueError("incomplete checkpoints: " + ",".join(incomplete))
    digest = _normalize_digest(str(document.get("checkpointsDigest", "")), "checkpoints")
    expected_digest = _canonical_digest(document, "checkpointsDigest")
    if verify_digest and digest != expected_digest:
        raise ValueError("checkpoint document digest mismatch")
    return execution, checkpoints, expected_digest


def finalize_checkpoints(
    document: dict[str, Any],
    candidate: dict[str, Any],
    apk: bytes,
    companion_archive_sha256: str,
) -> dict[str, Any]:
    gate_id = document.get("gateId")
    if not isinstance(gate_id, str) or gate_id not in ALL_GATES:
        raise ValueError("unknown checkpoint gate")
    environment_id = document.get("environmentId")
    if not isinstance(environment_id, str) or not ENVIRONMENT_RE.fullmatch(environment_id):
        raise ValueError("checkpoint environmentId is invalid")
    source, binding = _release_binding(candidate, apk, companion_archive_sha256)
    finalized = copy.deepcopy(document)
    _, _, digest = verify_checkpoints(
        finalized,
        gate_id=gate_id,
        expected_source=source,
        expected_binding=binding,
        expected_environment_id=environment_id,
        require_pass=True,
        verify_digest=False,
    )
    finalized["checkpointsDigest"] = digest
    verify_checkpoints(
        finalized,
        gate_id=gate_id,
        expected_source=source,
        expected_binding=binding,
        expected_environment_id=environment_id,
        require_pass=True,
    )
    return finalized


def build_gate(
    gate_id: str,
    candidate: dict[str, Any],
    apk: bytes,
    companion_archive_sha256: str,
    environment_id: str,
    checkpoints_document: dict[str, Any],
    evidence_path: Path,
    media_type: str,
    recorded_at: str,
) -> dict[str, Any]:
    if gate_id not in ALL_GATES:
        raise ValueError("unknown final-acceptance gate")
    source, binding = _release_binding(candidate, apk, companion_archive_sha256)
    if not ENVIRONMENT_RE.fullmatch(environment_id):
        raise ValueError("environmentId must be a bounded opaque identifier")
    if media_type not in MEDIA_TYPES:
        raise ValueError("unsupported evidence media type")
    _validate_timestamp(recorded_at)
    execution, checkpoints, checkpoints_digest = verify_checkpoints(
        checkpoints_document,
        gate_id=gate_id,
        expected_source=source,
        expected_binding=binding,
        expected_environment_id=environment_id,
        require_pass=True,
    )
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise ValueError("evidence file must be a regular non-symlink file")
    size = evidence_path.stat().st_size
    if size <= 0 or size > MAX_EVIDENCE_BYTES:
        raise ValueError("evidence file size is invalid")
    return {
        "schema": GATE_SCHEMA,
        "id": gate_id,
        "status": "PASS",
        "source": source,
        "binding": binding,
        "environmentId": environment_id,
        "execution": execution,
        "recordedAt": recorded_at,
        "checkpoints": checkpoints,
        "checkpointsDigest": checkpoints_digest,
        "evidence": {
            "sha256": _sha256_file(evidence_path),
            "sizeBytes": size,
            "mediaType": media_type,
            "retainedExternally": True,
        },
    }


def verify_gate(
    gate: dict[str, Any],
    *,
    expected_source: dict[str, str],
    expected_binding: dict[str, str],
) -> str:
    if set(gate) != {
        "schema",
        "id",
        "status",
        "source",
        "binding",
        "environmentId",
        "execution",
        "recordedAt",
        "checkpoints",
        "checkpointsDigest",
        "evidence",
    }:
        raise ValueError("final-acceptance gate has unexpected fields")
    if gate.get("schema") != GATE_SCHEMA or gate.get("status") != "PASS":
        raise ValueError("invalid final-acceptance gate schema/status")
    gate_id = gate.get("id")
    if not isinstance(gate_id, str) or gate_id not in ALL_GATES:
        raise ValueError("unknown final-acceptance gate")
    if gate.get("source") != expected_source:
        raise ValueError(f"{gate_id} source identity mismatch")
    if gate.get("binding") != expected_binding:
        raise ValueError(f"{gate_id} release-byte binding mismatch")
    environment_id = gate.get("environmentId")
    if not isinstance(environment_id, str) or not ENVIRONMENT_RE.fullmatch(environment_id):
        raise ValueError(f"{gate_id} environmentId is invalid")
    _validate_execution(gate.get("execution"), f"{gate_id} execution")
    _validate_timestamp(gate.get("recordedAt"))

    checkpoint_document = {
        "schema": CHECKPOINT_SCHEMA,
        "gateId": gate_id,
        "source": expected_source,
        "binding": expected_binding,
        "environmentId": environment_id,
        "execution": gate.get("execution"),
        "checkpoints": gate.get("checkpoints"),
        "checkpointsDigest": gate.get("checkpointsDigest"),
    }
    verify_checkpoints(
        checkpoint_document,
        gate_id=gate_id,
        expected_source=expected_source,
        expected_binding=expected_binding,
        expected_environment_id=environment_id,
        require_pass=True,
    )

    evidence = _mapping(gate.get("evidence"), f"{gate_id} evidence")
    if set(evidence) != {"sha256", "sizeBytes", "mediaType", "retainedExternally"}:
        raise ValueError(f"{gate_id} evidence has unexpected fields")
    _normalize_digest(str(evidence.get("sha256", "")), f"{gate_id} evidence")
    try:
        size = int(evidence.get("sizeBytes", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{gate_id} evidence size is invalid") from exc
    if size <= 0 or size > MAX_EVIDENCE_BYTES:
        raise ValueError(f"{gate_id} evidence size is invalid")
    if evidence.get("mediaType") not in MEDIA_TYPES or evidence.get("retainedExternally") is not True:
        raise ValueError(f"{gate_id} evidence retention/media contract is invalid")
    return gate_id


def build_manifest(
    profile: str,
    candidate: dict[str, Any],
    apk: bytes,
    companion_archive_sha256: str,
    gates: list[dict[str, Any]],
) -> dict[str, Any]:
    if profile not in PROFILE_RANK:
        raise ValueError("invalid final-acceptance profile")
    source, binding = _release_binding(candidate, apk, companion_archive_sha256)
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "profile": profile,
        "source": source,
        "binding": binding,
        "gates": gates,
        "claims": {
            "physicalEnvironmentAcceptanceRecorded": True,
            "deploymentReadinessRecorded": PROFILE_RANK[profile] >= PROFILE_RANK["deployment"],
            "productionTrafficReadinessRecorded": profile == "production-traffic",
            "releasePublished": False,
            "productionDeployed": False,
        },
    }
    manifest["acceptanceDigest"] = _canonical_digest(manifest, "acceptanceDigest")
    verify_manifest(
        manifest,
        candidate,
        apk,
        companion_archive_sha256,
        minimum_profile=profile,
    )
    return manifest


def verify_manifest(
    manifest: dict[str, Any],
    candidate: dict[str, Any],
    apk: bytes,
    companion_archive_sha256: str,
    *,
    minimum_profile: str = "publication",
    expected_repository: str | None = None,
    expected_sha: str | None = None,
    expected_version: str | None = None,
) -> None:
    if minimum_profile not in PROFILE_RANK:
        raise ValueError("invalid minimum profile")
    if set(manifest) != {"schema", "status", "profile", "source", "binding", "gates", "claims", "acceptanceDigest"}:
        raise ValueError("final acceptance manifest has unexpected fields")
    if manifest.get("schema") != SCHEMA or manifest.get("status") != "PASS":
        raise ValueError("invalid final acceptance schema/status")
    profile = manifest.get("profile")
    if not isinstance(profile, str) or profile not in PROFILE_RANK:
        raise ValueError("invalid final acceptance profile")
    if PROFILE_RANK[profile] < PROFILE_RANK[minimum_profile]:
        raise ValueError("final acceptance profile is weaker than required")

    source, expected_binding = _release_binding(candidate, apk, companion_archive_sha256)
    if manifest.get("source") != source:
        raise ValueError("final acceptance source does not match signed candidate")
    if expected_repository is not None and source["repository"] != expected_repository:
        raise ValueError("final acceptance repository mismatch")
    if expected_sha is not None and source["sha"] != expected_sha:
        raise ValueError("final acceptance source SHA mismatch")
    if expected_version is not None and source["version"] != expected_version:
        raise ValueError("final acceptance version mismatch")
    if manifest.get("binding") != expected_binding:
        raise ValueError("final acceptance release-byte binding mismatch")

    gates = manifest.get("gates")
    if not isinstance(gates, list) or not gates:
        raise ValueError("final acceptance gates must be a non-empty list")
    ids: list[str] = []
    for gate in gates:
        ids.append(verify_gate(_mapping(gate, "final-acceptance gate"), expected_source=source, expected_binding=expected_binding))
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate final-acceptance gate")
    gate_ids = set(ids)
    allowed = REQUIRED_GATES[profile] | OPTIONAL_GATES
    if not REQUIRED_GATES[profile].issubset(gate_ids):
        missing = sorted(REQUIRED_GATES[profile] - gate_ids)
        raise ValueError("missing required final-acceptance gates: " + ",".join(missing))
    if not gate_ids.issubset(allowed):
        raise ValueError("gate set exceeds selected final-acceptance profile")

    expected_claims = {
        "physicalEnvironmentAcceptanceRecorded": True,
        "deploymentReadinessRecorded": PROFILE_RANK[profile] >= PROFILE_RANK["deployment"],
        "productionTrafficReadinessRecorded": profile == "production-traffic",
        "releasePublished": False,
        "productionDeployed": False,
    }
    if manifest.get("claims") != expected_claims:
        raise ValueError("final acceptance claims mismatch")
    digest = _normalize_digest(str(manifest.get("acceptanceDigest", "")), "final acceptance")
    if digest != _canonical_digest(manifest, "acceptanceDigest"):
        raise ValueError("final acceptance digest mismatch")


def _load_candidate_and_apk(candidate_path: Path, apk_path: Path) -> tuple[dict[str, Any], bytes]:
    candidate = _read_json(candidate_path, "release candidate")
    if apk_path.is_symlink() or not apk_path.is_file():
        raise ValueError("APK must be a regular non-symlink file")
    size = apk_path.stat().st_size
    if size <= 0 or size > release_lineage.MAX_APK_BYTES:
        raise ValueError("APK size is invalid")
    return candidate, apk_path.read_bytes()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    template = sub.add_parser("checkpoint-template")
    template.add_argument("--id", required=True, choices=sorted(ALL_GATES))
    template.add_argument("--candidate", required=True, type=Path)
    template.add_argument("--apk", required=True, type=Path)
    template.add_argument("--companion-sha256-file", required=True, type=Path)
    template.add_argument("--environment-id", required=True)
    template.add_argument("--device-or-host", required=True)
    template.add_argument("--platform", required=True)
    template.add_argument("--tool", required=True)
    template.add_argument("--output", required=True, type=Path)

    finalize = sub.add_parser("checkpoint-finalize")
    finalize.add_argument("--input", required=True, type=Path)
    finalize.add_argument("--candidate", required=True, type=Path)
    finalize.add_argument("--apk", required=True, type=Path)
    finalize.add_argument("--companion-sha256-file", required=True, type=Path)
    finalize.add_argument("--output", required=True, type=Path)

    gate = sub.add_parser("gate")
    gate.add_argument("--id", required=True, choices=sorted(ALL_GATES))
    gate.add_argument("--candidate", required=True, type=Path)
    gate.add_argument("--apk", required=True, type=Path)
    gate.add_argument("--companion-sha256-file", required=True, type=Path)
    gate.add_argument("--environment-id", required=True)
    gate.add_argument("--checkpoints-file", required=True, type=Path)
    gate.add_argument("--evidence-file", required=True, type=Path)
    gate.add_argument("--media-type", required=True, choices=sorted(MEDIA_TYPES))
    gate.add_argument("--recorded-at", required=True)
    gate.add_argument("--output", required=True, type=Path)

    create = sub.add_parser("create")
    create.add_argument("--profile", required=True, choices=PROFILES)
    create.add_argument("--candidate", required=True, type=Path)
    create.add_argument("--apk", required=True, type=Path)
    create.add_argument("--companion-sha256-file", required=True, type=Path)
    create.add_argument("--gate", action="append", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)

    verify = sub.add_parser("verify")
    verify.add_argument("--input", required=True, type=Path)
    verify.add_argument("--candidate", required=True, type=Path)
    verify.add_argument("--apk", required=True, type=Path)
    verify.add_argument("--companion-sha256-file", required=True, type=Path)
    verify.add_argument("--minimum-profile", default="publication", choices=PROFILES)
    verify.add_argument("--expected-repository")
    verify.add_argument("--expected-sha")
    verify.add_argument("--expected-version")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "checkpoint-template":
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            companion = _read_companion_digest(args.companion_sha256_file)
            document = build_checkpoint_template(
                args.id,
                candidate,
                apk,
                companion,
                args.environment_id,
                {
                    "deviceOrHost": args.device_or_host,
                    "platform": args.platform,
                    "tool": args.tool,
                },
            )
            _write_json(args.output, document)
            print(f"checkpoint template {args.id}: PENDING")
        elif args.command == "checkpoint-finalize":
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            companion = _read_companion_digest(args.companion_sha256_file)
            document = _read_json(args.input, "checkpoint evidence")
            finalized = finalize_checkpoints(document, candidate, apk, companion)
            _write_json(args.output, finalized)
            print(f"checkpoint record {finalized['gateId']}: PASS")
        elif args.command == "gate":
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            companion = _read_companion_digest(args.companion_sha256_file)
            checkpoints = _read_json(args.checkpoints_file, "checkpoint evidence")
            gate_record = build_gate(
                args.id,
                candidate,
                apk,
                companion,
                args.environment_id,
                checkpoints,
                args.evidence_file,
                args.media_type,
                args.recorded_at,
            )
            _write_json(args.output, gate_record)
            print(f"final acceptance gate {args.id}: PASS")
        elif args.command == "create":
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            companion = _read_companion_digest(args.companion_sha256_file)
            gates = [_read_json(path, "gate evidence") for path in args.gate]
            manifest = build_manifest(args.profile, candidate, apk, companion, gates)
            _write_json(args.output, manifest)
            print(f"final release acceptance {args.profile}: PASS")
        else:
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            companion = _read_companion_digest(args.companion_sha256_file)
            manifest = _read_json(args.input, "final acceptance manifest")
            verify_manifest(
                manifest,
                candidate,
                apk,
                companion,
                minimum_profile=args.minimum_profile,
                expected_repository=args.expected_repository,
                expected_sha=args.expected_sha,
                expected_version=args.expected_version,
            )
            print(f"final release acceptance verified at minimum profile {args.minimum_profile}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"final release acceptance verification failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
