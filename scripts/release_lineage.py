#!/usr/bin/env python3
"""Bind Owner-gated release actions to canonical exact-SHA main evidence.

The pre-secret boundary verifies the GitHub-hosted Release Evidence Preflight
artifact before a signing job can reference signing material. The release
publication boundary consumes an already-signed release-candidate artifact and
never requires the Android signing key.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
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
MAX_PREFLIGHT_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_CANDIDATE_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_APK_BYTES = 200 * 1024 * 1024


def canonical_digest(document: dict[str, Any], digest_field: str) -> str:
    payload = copy.deepcopy(document)
    payload.pop(digest_field, None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


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


def _headers(token: str) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "sentinel-release-lineage/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _api_get(url: str, token: str, timeout: float = 20.0) -> Any:
    request = urllib.request.Request(url, headers=_headers(token))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(8 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", "replace")
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API network error: {exc.reason}") from exc
    if len(body) > 8 * 1024 * 1024:
        raise RuntimeError("GitHub API response exceeds safety limit")
    return json.loads(body)


class _CrossHostCredentialStrippingRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        old_host = urllib.parse.urlparse(req.full_url).netloc.lower()
        new_host = urllib.parse.urlparse(newurl).netloc.lower()
        if old_host != new_host:
            redirected.remove_header("Authorization")
        return redirected


def _download(url: str, token: str, max_bytes: int, timeout: float = 60.0) -> bytes:
    opener = urllib.request.build_opener(_CrossHostCredentialStrippingRedirect())
    request = urllib.request.Request(url, headers=_headers(token))
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", "replace")
        raise RuntimeError(f"artifact download HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"artifact download network error: {exc.reason}") from exc
    if len(body) > max_bytes:
        raise RuntimeError("artifact archive exceeds safety limit")
    return body


def _artifact_archive_url(repository: str, artifact_id: int) -> str:
    return f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip"


def _verify_archive_metadata(artifact: dict[str, Any], archive: bytes, *, expected_sha: str | None = None) -> str:
    if artifact.get("expired") is not False:
        raise ValueError("artifact is expired")
    digest = artifact.get("digest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise ValueError("artifact lacks a GitHub SHA-256 digest")
    size = int(artifact.get("size_in_bytes", 0))
    if size <= 0 or size != len(archive):
        raise ValueError("artifact archive size does not match GitHub metadata")
    actual = "sha256:" + hashlib.sha256(archive).hexdigest()
    if actual != digest:
        raise ValueError("artifact archive digest does not match GitHub metadata")
    workflow_run = artifact.get("workflow_run") or {}
    if expected_sha is not None and workflow_run.get("head_sha") != expected_sha:
        raise ValueError("artifact workflow source SHA mismatch")
    return digest


def _read_zip_exact(archive: bytes, expected_files: set[str], *, max_apk_bytes: int = MAX_APK_BYTES) -> dict[str, bytes]:
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
                raise ValueError(f"artifact member size invalid: {info.filename}")
            data = zf.read(info)
            if len(data) != info.file_size:
                raise ValueError(f"artifact member truncated: {info.filename}")
            result[info.filename] = data
        return result


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _latest_release_evidence_run(repository: str, sha: str, token: str, api_get: Callable[[str, str], Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"head_sha": sha, "event": "push", "per_page": 100})
    payload = api_get(f"https://api.github.com/repos/{repository}/actions/runs?{query}", token)
    candidates = [
        run
        for run in payload.get("workflow_runs", [])
        if run.get("name") == RELEASE_EVIDENCE_WORKFLOW
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


def _release_evidence_artifact(repository: str, run: dict[str, Any], sha: str, token: str, api_get: Callable[[str, str], Any]) -> dict[str, Any]:
    run_id = int(run["id"])
    payload = api_get(f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100", token)
    expected_name = f"sentinel-release-evidence-{sha}"
    candidates = [artifact for artifact in payload.get("artifacts", []) if artifact.get("name") == expected_name]
    if not candidates:
        raise ValueError("exact-SHA release-evidence artifact is missing")
    artifact = max(candidates, key=lambda item: int(item.get("id", 0)))
    if int(artifact.get("id", 0)) <= 0:
        raise ValueError("invalid release-evidence artifact identity")
    workflow_run = artifact.get("workflow_run") or {}
    if int(workflow_run.get("id", 0)) != run_id or workflow_run.get("head_sha") != sha:
        raise ValueError("release-evidence artifact is bound to a different workflow run or SHA")
    return artifact


def build_presecret_binding(
    repository: str,
    sha: str,
    version: str,
    token: str,
    *,
    api_get: Callable[[str, str], Any] = _api_get,
    downloader: Callable[[str, str, int], bytes] = _download,
) -> dict[str, Any]:
    _validate_identity(repository, sha, version)
    if not token:
        raise ValueError("GitHub token is required")
    run = _latest_release_evidence_run(repository, sha, token, api_get)
    artifact = _release_evidence_artifact(repository, run, sha, token, api_get)
    artifact_id = int(artifact["id"])
    archive = downloader(_artifact_archive_url(repository, artifact_id), token, MAX_PREFLIGHT_ARCHIVE_BYTES)
    artifact_digest = _verify_archive_metadata(artifact, archive, expected_sha=sha)
    files = _read_zip_exact(archive, {RELEASE_EVIDENCE_FILE})
    manifest = _json_object(files[RELEASE_EVIDENCE_FILE], "release evidence")

    enable_supply_chain_evidence()
    release_evidence.verify_manifest(
        manifest,
        expected_repository=repository,
        expected_sha=sha,
        expected_version=version,
    )
    source = manifest.get("source") or {}
    if source.get("event") != "push":
        raise ValueError("Owner-gated release actions require protected-main push evidence")

    binding: dict[str, Any] = {
        "schema": PRESECRET_SCHEMA,
        "status": "PASS",
        "generatedAt": manifest.get("generatedAt"),
        "source": {"repository": repository, "sha": sha, "version": version},
        "releaseEvidence": {
            "workflow": {
                "name": RELEASE_EVIDENCE_WORKFLOW,
                "path": RELEASE_EVIDENCE_WORKFLOW_PATH,
                "runId": int(run["id"]),
                "runAttempt": int(run["run_attempt"]),
                "event": "push",
                "headBranch": "main",
            },
            "artifact": {
                "id": artifact_id,
                "name": artifact["name"],
                "sizeBytes": int(artifact["size_in_bytes"]),
                "digest": artifact_digest,
                "expired": False,
                "headSha": sha,
            },
            "manifestDigest": manifest["evidenceDigest"],
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


def verify_presecret_binding(
    binding: dict[str, Any],
    *,
    expected_repository: str | None = None,
    expected_sha: str | None = None,
    expected_version: str | None = None,
) -> None:
    if binding.get("schema") != PRESECRET_SCHEMA or binding.get("status") != "PASS":
        raise ValueError("invalid pre-secret binding schema or status")
    source = binding.get("source")
    if not isinstance(source, dict):
        raise ValueError("pre-secret binding source missing")
    repository = source.get("repository")
    sha = source.get("sha")
    version = source.get("version")
    if not isinstance(repository, str) or not isinstance(sha, str) or not isinstance(version, str):
        raise ValueError("invalid pre-secret binding source")
    _validate_identity(repository, sha, version)
    if expected_repository is not None and repository != expected_repository:
        raise ValueError("pre-secret repository mismatch")
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("pre-secret source SHA mismatch")
    if expected_version is not None and version != expected_version:
        raise ValueError("pre-secret version mismatch")
    if not isinstance(binding.get("generatedAt"), str) or not binding["generatedAt"]:
        raise ValueError("pre-secret generatedAt missing")
    if binding.get("claims") != {
        "signingMaterialAccessed": False,
        "signedReleaseArtifact": False,
        "releasePublished": False,
        "productionDeployed": False,
    }:
        raise ValueError("pre-secret binding contains an invalid claim")

    evidence = binding.get("releaseEvidence")
    if not isinstance(evidence, dict):
        raise ValueError("release evidence binding missing")
    workflow = evidence.get("workflow")
    artifact = evidence.get("artifact")
    if not isinstance(workflow, dict) or not isinstance(artifact, dict):
        raise ValueError("release evidence workflow/artifact binding missing")
    if (
        workflow.get("name") != RELEASE_EVIDENCE_WORKFLOW
        or workflow.get("path") != RELEASE_EVIDENCE_WORKFLOW_PATH
        or workflow.get("event") != "push"
        or workflow.get("headBranch") != "main"
        or int(workflow.get("runId", 0)) <= 0
        or int(workflow.get("runAttempt", 0)) <= 0
    ):
        raise ValueError("invalid release-evidence workflow binding")
    if (
        artifact.get("name") != f"sentinel-release-evidence-{sha}"
        or artifact.get("expired") is not False
        or artifact.get("headSha") != sha
        or int(artifact.get("id", 0)) <= 0
        or int(artifact.get("sizeBytes", 0)) <= 0
        or not isinstance(artifact.get("digest"), str)
        or not DIGEST_RE.fullmatch(artifact["digest"])
    ):
        raise ValueError("invalid release-evidence artifact binding")
    manifest_digest = evidence.get("manifestDigest")
    if not isinstance(manifest_digest, str) or not DIGEST_RE.fullmatch(manifest_digest):
        raise ValueError("invalid release-evidence manifest digest")
    digest = binding.get("bindingDigest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise ValueError("invalid pre-secret binding digest")
    if digest != canonical_digest(binding, "bindingDigest"):
        raise ValueError("pre-secret binding digest mismatch")


def create_candidate_manifest(binding: dict[str, Any], apk: bytes, signer_sha256: str) -> dict[str, Any]:
    verify_presecret_binding(binding)
    if not apk or len(apk) > MAX_APK_BYTES:
        raise ValueError("release APK size is invalid")
    signer = normalize_fingerprint(signer_sha256)
    source = binding["source"]
    evidence = binding["releaseEvidence"]
    manifest: dict[str, Any] = {
        "schema": CANDIDATE_SCHEMA,
        "status": "PASS",
        "source": dict(source),
        "presecretBinding": {
            "bindingDigest": binding["bindingDigest"],
            "releaseEvidenceManifestDigest": evidence["manifestDigest"],
            "releaseEvidenceArtifactDigest": evidence["artifact"]["digest"],
            "releaseEvidenceRunId": evidence["workflow"]["runId"],
        },
        "artifact": {
            "name": APK_FILE,
            "sizeBytes": len(apk),
            "sha256": "sha256:" + hashlib.sha256(apk).hexdigest(),
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
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValueError("release-candidate source missing")
    repository = source.get("repository")
    sha = source.get("sha")
    version = source.get("version")
    if not isinstance(repository, str) or not isinstance(sha, str) or not isinstance(version, str):
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
    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError("release-candidate artifact metadata missing")
    apk_digest = "sha256:" + hashlib.sha256(apk).hexdigest()
    signer = artifact.get("signerSha256")
    if (
        artifact.get("name") != APK_FILE
        or int(artifact.get("sizeBytes", 0)) != len(apk)
        or artifact.get("sha256") != apk_digest
        or not isinstance(signer, str)
        or not FINGERPRINT_RE.fullmatch(signer)
    ):
        raise ValueError("release-candidate APK metadata mismatch")
    if expected_signer_sha256 is not None and signer != normalize_fingerprint(expected_signer_sha256):
        raise ValueError("release-candidate signer fingerprint mismatch")

    lineage = manifest.get("presecretBinding")
    if not isinstance(lineage, dict):
        raise ValueError("release-candidate pre-secret lineage missing")
    for key in ("bindingDigest", "releaseEvidenceManifestDigest", "releaseEvidenceArtifactDigest"):
        value = lineage.get(key)
        if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
            raise ValueError(f"invalid release-candidate lineage digest: {key}")
    if int(lineage.get("releaseEvidenceRunId", 0)) <= 0:
        raise ValueError("invalid release-candidate release-evidence run identity")
    if expected_binding is not None:
        verify_presecret_binding(
            expected_binding,
            expected_repository=repository,
            expected_sha=sha,
            expected_version=version,
        )
        evidence = expected_binding["releaseEvidence"]
        expected_lineage = {
            "bindingDigest": expected_binding["bindingDigest"],
            "releaseEvidenceManifestDigest": evidence["manifestDigest"],
            "releaseEvidenceArtifactDigest": evidence["artifact"]["digest"],
            "releaseEvidenceRunId": evidence["workflow"]["runId"],
        }
        if lineage != expected_lineage:
            raise ValueError("release-candidate lineage does not match current pre-secret binding")
    digest = manifest.get("candidateDigest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise ValueError("invalid release-candidate digest")
    if digest != canonical_digest(manifest, "candidateDigest"):
        raise ValueError("release-candidate digest mismatch")


def _find_candidate_artifact(repository: str, sha: str, token: str, api_get: Callable[[str, str], Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    query = urllib.parse.urlencode({"event": "workflow_dispatch", "branch": "main", "per_page": 100})
    runs = api_get(
        f"https://api.github.com/repos/{repository}/actions/workflows/release-candidate.yml/runs?{query}",
        token,
    ).get("workflow_runs", [])
    expected_name = f"sentinel-release-candidate-{sha}"
    for run in sorted(runs, key=lambda item: int(item.get("id", 0)), reverse=True):
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
        artifacts = api_get(
            f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100",
            token,
        ).get("artifacts", [])
        matches = [artifact for artifact in artifacts if artifact.get("name") == expected_name]
        if not matches:
            continue
        artifact = max(matches, key=lambda item: int(item.get("id", 0)))
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise ValueError("latest matching release-candidate workflow run is not successful")
        if artifact.get("expired") is not False:
            raise ValueError("release-candidate artifact is expired")
        if int(artifact.get("id", 0)) <= 0:
            raise ValueError("invalid release-candidate artifact identity")
        workflow_run = artifact.get("workflow_run") or {}
        if int(workflow_run.get("id", 0)) != run_id:
            raise ValueError("release-candidate artifact workflow identity mismatch")
        return run, artifact
    raise ValueError("no successful Owner release-candidate artifact exists for source SHA")


def fetch_candidate_package(
    repository: str,
    sha: str,
    version: str,
    token: str,
    binding: dict[str, Any],
    expected_signer_sha256: str,
    *,
    api_get: Callable[[str, str], Any] = _api_get,
    downloader: Callable[[str, str, int], bytes] = _download,
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]:
    _validate_identity(repository, sha, version)
    if not token:
        raise ValueError("GitHub token is required")
    verify_presecret_binding(binding, expected_repository=repository, expected_sha=sha, expected_version=version)
    run, artifact = _find_candidate_artifact(repository, sha, token, api_get)
    archive = downloader(_artifact_archive_url(repository, int(artifact["id"])), token, MAX_CANDIDATE_ARCHIVE_BYTES)
    artifact_digest = _verify_archive_metadata(artifact, archive)
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
    provenance = {
        "workflowRunId": int(run["id"]),
        "workflowRunAttempt": int(run.get("run_attempt", 1)),
        "artifactId": int(artifact["id"]),
        "artifactName": artifact["name"],
        "artifactDigest": artifact_digest,
    }
    return candidate, files, provenance


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    presecret = sub.add_parser("presecret")
    presecret.add_argument("--repository", required=True)
    presecret.add_argument("--sha", required=True)
    presecret.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
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
    fetch_candidate.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
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
            binding = build_presecret_binding(args.repository, args.sha, version, args.token)
            _write_json(Path(args.output), binding)
            print(f"pre-secret release binding PASS: {binding['bindingDigest']}")
        elif args.command == "verify-binding":
            binding = _read_json(Path(args.input))
            verify_presecret_binding(
                binding,
                expected_repository=args.expected_repository,
                expected_sha=args.expected_sha,
                expected_version=args.expected_version,
            )
            print(f"pre-secret release binding verified: {binding['bindingDigest']}")
        elif args.command == "create-candidate":
            binding = _read_json(Path(args.binding))
            apk = Path(args.apk).read_bytes()
            manifest = create_candidate_manifest(binding, apk, args.signer_sha256)
            _write_json(Path(args.output), manifest)
            print(f"release candidate manifest PASS: {manifest['candidateDigest']}")
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
            print(f"release candidate manifest verified: {manifest['candidateDigest']}")
        else:
            version = Path(args.version_file).read_text(encoding="utf-8").strip()
            binding = _read_json(Path(args.binding))
            candidate, files, provenance = fetch_candidate_package(
                args.repository,
                args.sha,
                version,
                args.token,
                binding,
                args.expected_signer_sha256,
            )
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            for name in (APK_FILE, PRESECRET_FILE, CANDIDATE_FILE):
                (output_dir / name).write_bytes(files[name])
            _write_json(output_dir / "release-candidate-provenance.json", provenance)
            print(
                "release candidate package verified: "
                f"{candidate['candidateDigest']} / {provenance['artifactDigest']}"
            )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"release lineage FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
