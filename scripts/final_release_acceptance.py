#!/usr/bin/env python3
"""Fail-closed exact-byte and structured-checkpoint release acceptance.

The verifier proves source/artifact consistency and that every gate records the
complete machine-readable checkpoint set. It still does not independently prove
that a human performed a physical observation; retained evidence plus the
Owner-authorized workflow dispatch remain the external observation claim.
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

SCHEMA = "sentinel.final-release-acceptance.v2"
GATE_SCHEMA = "sentinel.final-release-gate.v2"
CHECKPOINT_EVIDENCE_SCHEMA = "sentinel.acceptance-checkpoints.v1"
PROFILES = ("publication", "deployment", "production-traffic")
PROFILE_RANK = {name: index for index, name in enumerate(PROFILES)}

PUBLICATION_GATES = {
    "android-physical", "companion-host", "wow-exact-environment",
    "voice-acoustic", "accessibility-visual",
}
DEPLOYMENT_GATES = PUBLICATION_GATES | {
    "payment-provider-network", "voice-provider-network",
    "runtime-observability-provider", "production-database-recovery",
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

REQUIRED_CHECKPOINTS: dict[str, frozenset[str]] = {
    "android-physical": frozenset({
        "install-launch", "auth-session", "device-proof", "offline-reconnect",
        "background-resume", "diagnostics-export", "quality-report",
    }),
    "companion-host": frozenset({
        "archive-integrity", "launcher-login", "companion-active",
        "overlay-presentation", "restart-recovery", "game-launch",
    }),
    "wow-exact-environment": frozenset({
        "addon-load", "savedvariables-capture", "checkpoint-bridge",
        "core-observation", "passive-boundary",
    }),
    "voice-acoustic": frozenset({
        "consent", "microphone-capture", "stt-result", "voice-presentation",
        "stop-revoke",
    }),
    "accessibility-visual": frozenset({
        "screen-reader-navigation", "text-scaling", "contrast",
        "touch-targets", "reduced-motion",
    }),
    "payment-provider-network": frozenset({
        "sandbox-webhook-signature", "subscription-activation",
        "past-due-revocation", "cancellation-revocation", "replay-idempotency",
    }),
    "voice-provider-network": frozenset({
        "provider-tls", "stt-roundtrip", "tts-roundtrip", "timeout-failure",
        "consent-enforcement",
    }),
    "runtime-observability-provider": frozenset({
        "provider-tls", "event-delivery", "pii-scrub", "source-sha-correlation",
        "failure-path",
    }),
    "production-database-recovery": frozenset({
        "tls-connection", "backup-restore", "migration-replay", "rls-invariant",
        "recovery-rpo-rto",
    }),
    "production-ingress-readiness": frozenset({
        "https-tls", "body-limit", "security-headers", "rate-limit", "health-check",
    }),
    "runtime-security-penetration": frozenset({
        "authn-authz", "injection", "ssrf-egress", "secret-exposure",
        "rate-abuse", "report-reviewed",
    }),
    "firebase-test-lab": frozenset({"run-recorded"}),
}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ENVIRONMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
CHECKPOINT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MEDIA_TYPES = {"application/json"}
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
    value = path.read_text(encoding="utf-8")
    if len(value) > 256:
        raise ValueError("Companion digest file is too large")
    return _normalize_raw_sha256(value, "Companion archive")


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


def _candidate_binding(candidate: dict[str, Any], apk: bytes) -> tuple[dict[str, str], dict[str, str]]:
    release_lineage.verify_candidate_manifest(candidate, apk)
    source = _mapping(candidate.get("source"), "candidate source")
    repository, sha, version = source.get("repository"), source.get("sha"), source.get("version")
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
    return ({"repository": repository, "sha": sha, "version": version}, {"candidateDigest": candidate_digest, "androidApkSha256": apk_digest})


def _checkpoint_ids(evidence_path: Path, gate_id: str) -> tuple[str, ...]:
    evidence = _read_json(evidence_path, f"{gate_id} checkpoint evidence")
    if set(evidence) != {"schema", "gateId", "checkpoints"}:
        raise ValueError(f"{gate_id} checkpoint evidence has unexpected fields")
    if evidence.get("schema") != CHECKPOINT_EVIDENCE_SCHEMA or evidence.get("gateId") != gate_id:
        raise ValueError(f"{gate_id} checkpoint evidence identity mismatch")
    checkpoints = evidence.get("checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        raise ValueError(f"{gate_id} checkpoints must be a non-empty list")
    ids: list[str] = []
    for checkpoint in checkpoints:
        item = _mapping(checkpoint, f"{gate_id} checkpoint")
        if set(item) != {"id", "status"} or item.get("status") != "PASS":
            raise ValueError(f"{gate_id} checkpoint must contain only id and PASS status")
        cid = item.get("id")
        if not isinstance(cid, str) or not CHECKPOINT_RE.fullmatch(cid):
            raise ValueError(f"{gate_id} checkpoint id is invalid")
        ids.append(cid)
    if len(ids) != len(set(ids)):
        raise ValueError(f"{gate_id} has duplicate checkpoints")
    actual = frozenset(ids)
    required = REQUIRED_CHECKPOINTS[gate_id]
    if actual != required:
        missing = sorted(required - actual)
        unexpected = sorted(actual - required)
        raise ValueError(f"{gate_id} checkpoint set mismatch; missing={missing}; unexpected={unexpected}")
    return tuple(sorted(ids))


def build_gate(gate_id: str, candidate: dict[str, Any], apk: bytes, companion_archive_sha256: str, environment_id: str, evidence_path: Path, media_type: str, recorded_at: str) -> dict[str, Any]:
    if gate_id not in ALL_GATES:
        raise ValueError("unknown final-acceptance gate")
    source, binding = _candidate_binding(candidate, apk)
    companion_digest = _normalize_raw_sha256(companion_archive_sha256, "Companion archive")
    if not ENVIRONMENT_RE.fullmatch(environment_id):
        raise ValueError("environmentId must be a bounded opaque identifier")
    if media_type != "application/json":
        raise ValueError("final acceptance evidence must be machine-readable application/json")
    _validate_timestamp(recorded_at)
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise ValueError("evidence file must be a regular non-symlink file")
    size = evidence_path.stat().st_size
    if size <= 0 or size > MAX_EVIDENCE_BYTES:
        raise ValueError("evidence file size is invalid")
    checkpoints = _checkpoint_ids(evidence_path, gate_id)
    return {
        "schema": GATE_SCHEMA,
        "id": gate_id,
        "status": "PASS",
        "source": source,
        "binding": {**binding, "companionArchiveSha256": companion_digest},
        "environmentId": environment_id,
        "recordedAt": recorded_at,
        "checkpoints": list(checkpoints),
        "evidence": {
            "sha256": _sha256_file(evidence_path),
            "sizeBytes": size,
            "mediaType": media_type,
            "retainedExternally": True,
        },
    }


def verify_gate(gate: dict[str, Any], *, expected_source: dict[str, str], expected_binding: dict[str, str]) -> str:
    expected_fields = {"schema", "id", "status", "source", "binding", "environmentId", "recordedAt", "checkpoints", "evidence"}
    if set(gate) != expected_fields:
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
    _validate_timestamp(gate.get("recordedAt"))
    checkpoints = gate.get("checkpoints")
    if not isinstance(checkpoints, list) or frozenset(checkpoints) != REQUIRED_CHECKPOINTS[gate_id] or len(checkpoints) != len(set(checkpoints)):
        raise ValueError(f"{gate_id} checkpoint set mismatch")
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
    if evidence.get("mediaType") != "application/json" or evidence.get("retainedExternally") is not True:
        raise ValueError(f"{gate_id} evidence retention/media contract is invalid")
    return gate_id


def build_manifest(profile: str, candidate: dict[str, Any], apk: bytes, companion_archive_sha256: str, gates: list[dict[str, Any]]) -> dict[str, Any]:
    if profile not in PROFILE_RANK:
        raise ValueError("invalid final-acceptance profile")
    source, candidate_binding = _candidate_binding(candidate, apk)
    binding = {**candidate_binding, "companionArchiveSha256": _normalize_raw_sha256(companion_archive_sha256, "Companion archive")}
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
    verify_manifest(manifest, candidate, apk, companion_archive_sha256, minimum_profile=profile)
    return manifest


def verify_manifest(manifest: dict[str, Any], candidate: dict[str, Any], apk: bytes, companion_archive_sha256: str, *, minimum_profile: str = "publication", expected_repository: str | None = None, expected_sha: str | None = None, expected_version: str | None = None) -> None:
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
    source, candidate_binding = _candidate_binding(candidate, apk)
    if manifest.get("source") != source:
        raise ValueError("final acceptance source does not match signed candidate")
    if expected_repository is not None and source["repository"] != expected_repository:
        raise ValueError("final acceptance repository mismatch")
    if expected_sha is not None and source["sha"] != expected_sha:
        raise ValueError("final acceptance source SHA mismatch")
    if expected_version is not None and source["version"] != expected_version:
        raise ValueError("final acceptance version mismatch")
    expected_binding = {**candidate_binding, "companionArchiveSha256": _normalize_raw_sha256(companion_archive_sha256, "Companion archive")}
    if manifest.get("binding") != expected_binding:
        raise ValueError("final acceptance release-byte binding mismatch")
    gates = manifest.get("gates")
    if not isinstance(gates, list) or not gates:
        raise ValueError("final acceptance gates must be a non-empty list")
    ids = [verify_gate(_mapping(gate, "final-acceptance gate"), expected_source=source, expected_binding=expected_binding) for gate in gates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate final-acceptance gate")
    gate_ids = set(ids)
    allowed = REQUIRED_GATES[profile] | OPTIONAL_GATES
    if not REQUIRED_GATES[profile].issubset(gate_ids):
        raise ValueError("missing required final-acceptance gates: " + ",".join(sorted(REQUIRED_GATES[profile] - gate_ids)))
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    gate = sub.add_parser("gate")
    gate.add_argument("--id", required=True, choices=sorted(ALL_GATES))
    gate.add_argument("--candidate", required=True, type=Path)
    gate.add_argument("--apk", required=True, type=Path)
    gate.add_argument("--companion-sha256-file", required=True, type=Path)
    gate.add_argument("--environment-id", required=True)
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
        if args.command == "gate":
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            gate = build_gate(args.id, candidate, apk, _read_companion_digest(args.companion_sha256_file), args.environment_id, args.evidence_file, args.media_type, args.recorded_at)
            args.output.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"final acceptance gate {args.id}: PASS")
        elif args.command == "create":
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            gates = [_read_json(path, "gate evidence") for path in args.gate]
            manifest = build_manifest(args.profile, candidate, apk, _read_companion_digest(args.companion_sha256_file), gates)
            args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"final release acceptance {args.profile}: PASS")
        else:
            candidate, apk = _load_candidate_and_apk(args.candidate, args.apk)
            manifest = _read_json(args.input, "final acceptance manifest")
            verify_manifest(manifest, candidate, apk, _read_companion_digest(args.companion_sha256_file), minimum_profile=args.minimum_profile, expected_repository=args.expected_repository, expected_sha=args.expected_sha, expected_version=args.expected_version)
            print(f"final release acceptance verified at minimum profile {args.minimum_profile}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"final release acceptance verification failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
