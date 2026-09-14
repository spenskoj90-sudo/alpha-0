#!/usr/bin/env python3
"""Exact-SHA release lineage with transient authenticated GitHub verification.

GitHub authentication belongs to the ``gh`` subprocess inherited from the
workflow environment. Python never reads, receives, serializes, or logs the
credential. Authenticated workflow/artifact metadata is validated transiently
and is never persisted in release-lineage JSON.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import subprocess
import sys
import urllib.parse
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import release_evidence
from release_evidence_entrypoint import enable_supply_chain_evidence

PRESECRET_SCHEMA = "sentinel.release-presecret-binding.v1"
CANDIDATE_SCHEMA = "sentinel.release-candidate.v1"
RELEASE_EVIDENCE_WORKFLOW = "Release Evidence Preflight"
RELEASE_EVIDENCE_WORKFLOW_PATH = ".github/workflows/release-evidence.yml"
RELEASE_CANDIDATE_WORKFLOW = "Release Candidate Artifact"
RELEASE_CANDIDATE_WORKFLOW_PATH = ".github/workflows/release-candidate.yml"
RELEASE_EVIDENCE_FILE = "release-evidence.json"
PRESECRET_FILE = "release-presecret-binding.json"
CANDIDATE_FILE = "release-candidate.json"
APK_FILE = "app-release.apk"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FINGERPRINT_RE = re.compile(r"^[0-9A-F]{64}$")
MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_PREFLIGHT_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_CANDIDATE_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_APK_BYTES = 200 * 1024 * 1024

ApiGet = Callable[[str], Any]
Downloader = Callable[[str, int], bytes]


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_digest(document: dict[str, Any], digest_field: str) -> str:
    payload = copy.deepcopy(document)
    payload.pop(digest_field, None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256(encoded)


def normalize_fingerprint(value: str) -> str:
    normalized = value.replace(":", "").strip().upper()
    if not FINGERPRINT_RE.fullmatch(normalized):
        raise ValueError("signer SHA-256 fingerprint must contain exactly 64 hexadecimal characters")
    return normalized


def _validate_identity(repository: str, sha: str, version: str) -> None:
    if not REPO_RE.fullmatch(repository):
        raise ValueError("repository must be owner/name")
    if not SHA_RE.fullmatch(sha):
        raise ValueError("source SHA must be 40 lowercase hexadecimal characters")
    if not version.strip():
        raise ValueError("version is empty")


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise ValueError(f"invalid {label} digest")
    return value


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid {label}")
    return value


def _run_gh_api(endpoint: str, max_bytes: int, timeout: float) -> bytes:
    """GET one fixed GitHub REST endpoint via gh without exposing its credential."""
    if not endpoint.startswith("/repos/") or any(char in endpoint for char in "\r\n"):
        raise ValueError("invalid GitHub API endpoint")
    if max_bytes <= 0:
        raise ValueError("invalid GitHub API response limit")
    try:
        completed = subprocess.run(
            ["gh", "api", "--method", "GET", endpoint],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("GitHub API request failed") from exc
    if completed.returncode != 0:
        raise RuntimeError("GitHub API request failed")
    if len(completed.stdout) > max_bytes:
        raise RuntimeError("GitHub API response exceeds safety limit")
    return completed.stdout


def _gh_api_get(endpoint: str) -> Any:
    try:
        return json.loads(_run_gh_api(endpoint, MAX_API_RESPONSE_BYTES, 20.0))
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub API returned invalid JSON") from exc


def _gh_api_download(endpoint: str, max_bytes: int) -> bytes:
    return _run_gh_api(endpoint, max_bytes, 60.0)


def _artifact_archive_endpoint(repository: str, artifact_id: int) -> str:
    if not REPO_RE.fullmatch(repository) or artifact_id <= 0:
        raise ValueError("invalid artifact archive identity")
    return f"/repos/{repository}/actions/artifacts/{artifact_id}/zip"


def _verify_archive_metadata(
    artifact: dict[str, Any],
    archive: bytes,
    *,
    expected_sha: str | None = None,
) -> None:
    if artifact.get("expired") is not False:
        raise ValueError("artifact is expired")
    github_digest = _require_digest(artifact.get("digest"), "artifact metadata")
    size = int(artifact.get("size_in_bytes", 0))
    if size <= 0 or size != len(archive):
        raise ValueError("artifact archive size does not match GitHub metadata")
    if _sha256(archive) != github_digest:
        raise ValueError("artifact archive digest does not match GitHub metadata")
    workflow_run = _mapping(artifact.get("workflow_run") or {}, "artifact workflow binding")
    if expected_sha is not None and workflow_run.get("head_sha") != expected_sha:
        raise ValueError("artifact workflow source SHA mismatch")


def _read_zip_exact(
    archive: bytes,
    expected_files: set[str],
    *,
    max_apk_bytes: int = MAX_APK_BYTES,
) -> dict[str, bytes]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise ValueError("artifact is not a valid ZIP archive") from exc
    with zf:
        infos = zf.infolist()
        if any(info.is_dir() for info in infos):
            raise ValueError("artifact archive must not contain directory entries")
        names: list[str] = []
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
                raise ValueError("artifact archive contains an unsafe or nested path")
            names.append(info.filename)
        if len(names) != len(set(names)):
            raise ValueError("artifact archive contains duplicate paths")
        if set(names) != expected_files:
            raise ValueError("artifact archive file set mismatch")
        result: dict[str, bytes] = {}
        for info in infos:
            limit = max_apk_bytes if info.filename == APK_FILE else MAX_JSON_BYTES
            if info.file_size <= 0 or info.file_size > limit:
                raise ValueError("artifact member size invalid")
            data = zf.read(info)
            if len(data) != info.file_size:
                raise ValueError("artifact member truncated")
            result[info.filename] = data
        return result


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    if not data or len(data) > MAX_JSON_BYTES:
        raise ValueError(f"invalid {label} size")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _latest_release_evidence_run(repository: str, sha: str, api_get: ApiGet) -> dict[str, Any]:
    query = urllib.parse.urlencode({"head_sha": sha, "event": "push", "per_page": 100})
    payload = _mapping(api_get(f"/repos/{repository}/actions/runs?{query}"), "workflow runs response")
    candidates = [
        run
        for run in payload.get("workflow_runs", [])
        if isinstance(run, dict)
        and run.get("name") == RELEASE_EVIDENCE_WORKFLOW
        and run.get("path") == RELEASE_EVIDENCE_WORKFLOW_PATH
        and run.get("head_sha") == sha
        and run.get("head_branch") == "main"
        and run.get("event") == "push"
    ]
    if not candidates:
        raise ValueError("no protected-main Release Evidence Preflight run exists for source SHA")
    run = max(candidates, key=lambda item: int(item.get("id", 0)))
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise ValueError("latest protected-main Release Evidence Preflight is not successful")
    if int(run.get("id", 0)) <= 0 or int(run.get("run_attempt", 0)) <= 0:
        raise ValueError("invalid release-evidence workflow run identity")
    return run


def _release_evidence_artifact(
    repository: str,
    run: dict[str, Any],
    sha: str,
    api_get: ApiGet,
) -> dict[str, Any]:
    run_id = int(run["id"])
    payload = _mapping(
        api_get(f"/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"),
        "artifact response",
    )
    expected_name = f"sentinel-release-evidence-{sha}"
    candidates = [
        artifact
        for artifact in payload.get("artifacts", [])
        if isinstance(artifact, dict) and artifact.get("name") == expected_name
    ]
    if not candidates:
        raise ValueError("exact-SHA release-evidence artifact is missing")
    artifact = max(candidates, key=lambda item: int(item.get("id", 0)))
    workflow_run = _mapping(artifact.get("workflow_run") or {}, "release-evidence artifact workflow binding")
    if int(artifact.get("id", 0)) <= 0:
        raise ValueError("invalid release-evidence artifact identity")
    if int(workflow_run.get("id", 0)) != run_id or workflow_run.get("head_sha") != sha:
        raise ValueError("release-evidence artifact is bound to a different workflow run or SHA")
    return artifact


def _verify_live_release_evidence(
    repository: str,
    sha: str,
    version: str,
    *,
    api_get: ApiGet,
    downloader: Downloader,
) -> None:
    """Validate authenticated GitHub evidence without returning persistable data."""
    run = _latest_release_evidence_run(repository, sha, api_get)
    artifact = _release_evidence_artifact(repository, run, sha, api_get)
    archive = downloader(
        _artifact_archive_endpoint(repository, int(artifact["id"])),
        MAX_PREFLIGHT_ARCHIVE_BYTES,
    )
    _verify_archive_metadata(artifact, archive, expected_sha=sha)
    files = _read_zip_exact(archive, {RELEASE_EVIDENCE_FILE})
    manifest = _json_object(files[RELEASE_EVIDENCE_FILE], "release evidence")

    enable_supply_chain_evidence()
    release_evidence.verify_manifest(
        manifest,
        expected_repository=repository,
        expected_sha=sha,
        expected_version=version,
    )
    if _mapping(manifest.get("source") or {}, "release evidence source").get("event") != "push":
        raise ValueError("Owner-gated release actions require protected-main push evidence")


def _binding_from_identity(repository: str, sha: str, version: str) -> dict[str, Any]:
    """Create the deterministic persistable binding from public source identity only."""
    _validate_identity(repository, sha, version)
    binding: dict[str, Any] = {
        "schema": PRESECRET_SCHEMA,
        "status": "PASS",
        "source": {"repository": repository, "sha": sha, "version": version},
        "releaseEvidence": {
            "workflow": {
                "name": RELEASE_EVIDENCE_WORKFLOW,
                "path": RELEASE_EVIDENCE_WORKFLOW_PATH,
                "event": "push",
                "headBranch": "main",
            },
            "artifact": {
                "name": f"sentinel-release-evidence-{sha}",
                "headSha": sha,
            },
        },
        "claims": {
            "signingMaterialAccessed": False,
            "signedReleaseArtifact": False,
            "releasePublished": False,
            "productionDeployed": False,
        },
    }
    binding["bindingDigest"] = canonical_digest(binding, "bindingDigest")
    verify_presecret_binding(binding, expected_repository=repository, expected_sha=sha, expected_version=version)
    return binding


def build_presecret_binding(
    repository: str,
    sha: str,
    version: str,
    *,
    api_get: ApiGet = _gh_api_get,
    downloader: Downloader = _gh_api_download,
) -> dict[str, Any]:
    _validate_identity(repository, sha, version)
    _verify_live_release_evidence(
        repository,
        sha,
        version,
        api_get=api_get,
        downloader=downloader,
    )
    return _binding_from_identity(repository, sha, version)


def verify_presecret_binding(
    binding: dict[str, Any],
    *,
    expected_repository: str | None = None,
    expected_sha: str | None = None,
    expected_version: str | None = None,
) -> None:
    if binding.get("schema") != PRESECRET_SCHEMA or binding.get("status") != "PASS":
        raise ValueError("invalid pre-secret binding schema or status")
    source = _mapping(binding.get("source"), "pre-secret binding source")
    repository, sha, version = source.get("repository"), source.get("sha"), source.get("version")
    if not all(isinstance(value, str) for value in (repository, sha, version)):
        raise ValueError("invalid pre-secret binding source")
    _validate_identity(repository, sha, version)
    if expected_repository is not None and repository != expected_repository:
        raise ValueError("pre-secret repository mismatch")
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("pre-secret source SHA mismatch")
    if expected_version is not None and version != expected_version:
        raise ValueError("pre-secret version mismatch")
    if binding.get("claims") != {
        "signingMaterialAccessed": False,
        "signedReleaseArtifact": False,
        "releasePublished": False,
        "productionDeployed": False,
    }:
        raise ValueError("pre-secret binding contains an invalid claim")

    evidence = _mapping(binding.get("releaseEvidence"), "release evidence binding")
    workflow = _mapping(evidence.get("workflow"), "release evidence workflow binding")
    artifact = _mapping(evidence.get("artifact"), "release evidence artifact binding")
    if workflow != {
        "name": RELEASE_EVIDENCE_WORKFLOW,
        "path": RELEASE_EVIDENCE_WORKFLOW_PATH,
        "event": "push",
        "headBranch": "main",
    }:
        raise ValueError("invalid release-evidence workflow binding")
    if artifact != {
        "name": f"sentinel-release-evidence-{sha}",
        "headSha": sha,
    }:
        raise ValueError("invalid release-evidence artifact binding")
    if set(evidence) != {"workflow", "artifact"}:
        raise ValueError("unexpected persisted release-evidence metadata")

    digest = _require_digest(binding.get("bindingDigest"), "pre-secret binding")
    if digest != canonical_digest(binding, "bindingDigest"):
        raise ValueError("pre-secret binding digest mismatch")


def create_candidate_manifest(binding: dict[str, Any], apk: bytes, signer_sha256: str) -> dict[str, Any]:
    verify_presecret_binding(binding)
    if not apk or len(apk) > MAX_APK_BYTES:
        raise ValueError("release APK size is invalid")
    signer = normalize_fingerprint(signer_sha256)
    manifest: dict[str, Any] = {
        "schema": CANDIDATE_SCHEMA,
        "status": "PASS",
        "source": dict(binding["source"]),
        "presecretBinding": {"bindingDigest": binding["bindingDigest"]},
        "artifact": {
            "name": APK_FILE,
            "sizeBytes": len(apk),
            "sha256": _sha256(apk),
            "signerSha256": signer,
        },
        "claims": {
            "signedReleaseArtifact": True,
            "releasePublished": False,
            "productionDeployed": False,
        },
    }
    manifest["candidateDigest"] = canonical_digest(manifest, "candidateDigest")
    verify_candidate_manifest(manifest, apk, expected_binding=binding, expected_signer_sha256=signer)
    return manifest


def verify_candidate_manifest(
    manifest: dict[str, Any],
    apk: bytes,
    *,
    expected_binding: dict[str, Any] | None = None,
    expected_repository: str | None = None,
    expected_sha: str | None = None,
    expected_version: str | None = None,
    expected_signer_sha256: str | None = None,
) -> None:
    if manifest.get("schema") != CANDIDATE_SCHEMA or manifest.get("status") != "PASS":
        raise ValueError("invalid release-candidate schema or status")
    source = _mapping(manifest.get("source"), "release-candidate source")
    repository, sha, version = source.get("repository"), source.get("sha"), source.get("version")
    if not all(isinstance(value, str) for value in (repository, sha, version)):
        raise ValueError("invalid release-candidate source")
    _validate_identity(repository, sha, version)
    if expected_repository is not None and repository != expected_repository:
        raise ValueError("release-candidate repository mismatch")
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("release-candidate source SHA mismatch")
    if expected_version is not None and version != expected_version:
        raise ValueError("release-candidate version mismatch")
    if manifest.get("claims") != {
        "signedReleaseArtifact": True,
        "releasePublished": False,
        "productionDeployed": False,
    }:
        raise ValueError("invalid release-candidate claims")
    if not apk or len(apk) > MAX_APK_BYTES:
        raise ValueError("release APK size is invalid")

    artifact = _mapping(manifest.get("artifact"), "release-candidate artifact metadata")
    signer = artifact.get("signerSha256")
    if (
        artifact.get("name") != APK_FILE
        or int(artifact.get("sizeBytes", 0)) != len(apk)
        or artifact.get("sha256") != _sha256(apk)
        or not isinstance(signer, str)
        or not FINGERPRINT_RE.fullmatch(signer)
    ):
        raise ValueError("release-candidate APK metadata mismatch")
    if expected_signer_sha256 is not None and signer != normalize_fingerprint(expected_signer_sha256):
        raise ValueError("release-candidate signer fingerprint mismatch")

    lineage = _mapping(manifest.get("presecretBinding"), "release-candidate pre-secret lineage")
    _require_digest(lineage.get("bindingDigest"), "release-candidate binding")
    if set(lineage) != {"bindingDigest"}:
        raise ValueError("unexpected release-candidate lineage metadata")
    if expected_binding is not None:
        verify_presecret_binding(
            expected_binding,
            expected_repository=repository,
            expected_sha=sha,
            expected_version=version,
        )
        if lineage != {"bindingDigest": expected_binding["bindingDigest"]}:
            raise ValueError("release-candidate lineage does not match current pre-secret binding")

    digest = _require_digest(manifest.get("candidateDigest"), "release-candidate")
    if digest != canonical_digest(manifest, "candidateDigest"):
        raise ValueError("release-candidate digest mismatch")


def _find_candidate_artifact(
    repository: str,
    sha: str,
    api_get: ApiGet,
) -> dict[str, Any]:
    query = urllib.parse.urlencode({"event": "workflow_dispatch", "branch": "main", "per_page": 100})
    payload = _mapping(
        api_get(f"/repos/{repository}/actions/workflows/release-candidate.yml/runs?{query}"),
        "release-candidate runs response",
    )
    runs = payload.get("workflow_runs", [])
    expected_name = f"sentinel-release-candidate-{sha}"
    for run in sorted(
        (item for item in runs if isinstance(item, dict)),
        key=lambda item: int(item.get("id", 0)),
        reverse=True,
    ):
        if (
            run.get("name") != RELEASE_CANDIDATE_WORKFLOW
            or run.get("path") != RELEASE_CANDIDATE_WORKFLOW_PATH
            or run.get("event") != "workflow_dispatch"
            or run.get("head_branch") != "main"
        ):
            continue
        run_id = int(run.get("id", 0))
        if run_id <= 0:
            continue
        artifacts_payload = _mapping(
            api_get(f"/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"),
            "release-candidate artifact response",
        )
        matches = [
            artifact
            for artifact in artifacts_payload.get("artifacts", [])
            if isinstance(artifact, dict) and artifact.get("name") == expected_name
        ]
        if not matches:
            continue
        artifact = max(matches, key=lambda item: int(item.get("id", 0)))
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise ValueError("latest matching release-candidate workflow run is not successful")
        if artifact.get("expired") is not False or int(artifact.get("id", 0)) <= 0:
            raise ValueError("release-candidate artifact is unavailable")
        workflow_run = _mapping(artifact.get("workflow_run") or {}, "release-candidate artifact workflow binding")
        if int(workflow_run.get("id", 0)) != run_id:
            raise ValueError("release-candidate artifact workflow identity mismatch")
        return artifact
    raise ValueError("no successful Owner release-candidate artifact exists for source SHA")


def fetch_candidate_package(
    repository: str,
    sha: str,
    version: str,
    binding: dict[str, Any],
    expected_signer_sha256: str,
    *,
    api_get: ApiGet = _gh_api_get,
    downloader: Downloader = _gh_api_download,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    _validate_identity(repository, sha, version)
    verify_presecret_binding(binding, expected_repository=repository, expected_sha=sha, expected_version=version)
    artifact = _find_candidate_artifact(repository, sha, api_get)
    archive = downloader(
        _artifact_archive_endpoint(repository, int(artifact["id"])),
        MAX_CANDIDATE_ARCHIVE_BYTES,
    )
    _verify_archive_metadata(artifact, archive)
    files = _read_zip_exact(archive, {APK_FILE, PRESECRET_FILE, CANDIDATE_FILE})

    packaged_binding = _json_object(files[PRESECRET_FILE], "packaged pre-secret binding")
    verify_presecret_binding(
        packaged_binding,
        expected_repository=repository,
        expected_sha=sha,
        expected_version=version,
    )
    if packaged_binding["bindingDigest"] != binding["bindingDigest"]:
        raise ValueError("packaged pre-secret binding is stale or different from current canonical evidence")

    candidate = _json_object(files[CANDIDATE_FILE], "release candidate")
    verify_candidate_manifest(
        candidate,
        files[APK_FILE],
        expected_binding=packaged_binding,
        expected_repository=repository,
        expected_sha=sha,
        expected_version=version,
        expected_signer_sha256=expected_signer_sha256,
    )
    return candidate, files


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError("unable to read JSON input") from exc
    return _json_object(data, "JSON input")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    presecret = sub.add_parser("presecret")
    presecret.add_argument("--repository", required=True)
    presecret.add_argument("--sha", required=True)
    presecret.add_argument("--version-file", default="VERSION")
    presecret.add_argument("--output", required=True)

    verify_binding = sub.add_parser("verify-binding")
    verify_binding.add_argument("--input", required=True)
    verify_binding.add_argument("--expected-repository")
    verify_binding.add_argument("--expected-sha")
    verify_binding.add_argument("--expected-version")

    create_candidate = sub.add_parser("create-candidate")
    create_candidate.add_argument("--binding", required=True)
    create_candidate.add_argument("--apk", required=True)
    create_candidate.add_argument("--signer-sha256", required=True)
    create_candidate.add_argument("--output", required=True)

    verify_candidate = sub.add_parser("verify-candidate")
    verify_candidate.add_argument("--input", required=True)
    verify_candidate.add_argument("--binding", required=True)
    verify_candidate.add_argument("--apk", required=True)
    verify_candidate.add_argument("--expected-repository")
    verify_candidate.add_argument("--expected-sha")
    verify_candidate.add_argument("--expected-version")
    verify_candidate.add_argument("--expected-signer-sha256")

    fetch_candidate = sub.add_parser("fetch-candidate")
    fetch_candidate.add_argument("--repository", required=True)
    fetch_candidate.add_argument("--sha", required=True)
    fetch_candidate.add_argument("--version-file", default="VERSION")
    fetch_candidate.add_argument("--binding", required=True)
    fetch_candidate.add_argument("--expected-signer-sha256", required=True)
    fetch_candidate.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "presecret":
            version = Path(args.version_file).read_text(encoding="utf-8").strip()
            binding = build_presecret_binding(args.repository, args.sha, version)
            _write_json(Path(args.output), binding)
            print("pre-secret release binding PASS")
        elif args.command == "verify-binding":
            binding = _read_json(Path(args.input))
            verify_presecret_binding(
                binding,
                expected_repository=args.expected_repository,
                expected_sha=args.expected_sha,
                expected_version=args.expected_version,
            )
            print("pre-secret release binding verified")
        elif args.command == "create-candidate":
            binding = _read_json(Path(args.binding))
            apk = Path(args.apk).read_bytes()
            manifest = create_candidate_manifest(binding, apk, args.signer_sha256)
            _write_json(Path(args.output), manifest)
            print("release candidate manifest PASS")
        elif args.command == "verify-candidate":
            manifest = _read_json(Path(args.input))
            binding = _read_json(Path(args.binding))
            apk = Path(args.apk).read_bytes()
            verify_candidate_manifest(
                manifest,
                apk,
                expected_binding=binding,
                expected_repository=args.expected_repository,
                expected_sha=args.expected_sha,
                expected_version=args.expected_version,
                expected_signer_sha256=args.expected_signer_sha256,
            )
            print("release candidate manifest verified")
        else:
            version = Path(args.version_file).read_text(encoding="utf-8").strip()
            binding = _read_json(Path(args.binding))
            _, files = fetch_candidate_package(
                args.repository,
                args.sha,
                version,
                binding,
                args.expected_signer_sha256,
            )
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            for name in (APK_FILE, PRESECRET_FILE, CANDIDATE_FILE):
                (output_dir / name).write_bytes(files[name])
            print("release candidate package verified")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
        print("release lineage FAIL", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
