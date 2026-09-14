#!/usr/bin/env python3
"""Collect and verify exact-SHA release-readiness evidence from GitHub Actions.

This tool is intentionally a preflight evidence boundary. It does not sign artifacts,
publish releases, deploy production, or claim environment acceptance.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SCHEMA = "sentinel.release-evidence.v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

BUILD_JOBS = (
    "Repository verification",
    "Core tests and coverage",
    "PostgreSQL integration and recovery",
    "Android build and tests",
    "Android instrumentation (GitHub Emulator)",
    "Web build",
    "Launcher runtime tests",
    "Block D operational evidence",
    "Container build",
    "Reproducible container build comparison",
    "Deployment smoke and health",
)

WORKFLOW_SPECS: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "push": {
        "Build & Test": {
            "jobs": BUILD_JOBS,
            "artifacts": (
                "alpha-0-android-instrumentation-{sha}",
                "block-d-operational-evidence-{sha}",
            ),
        },
        "Security": {
            "jobs": (
                "Secret and image scan",
                "Dependency audit",
                "CodeQL (python)",
                "CodeQL (javascript)",
            ),
            "artifacts": (),
        },
        "P1 Evidence": {
            "jobs": ("P1 evidence artifacts",),
            "artifacts": ("sentinel-p1-evidence-{sha}",),
        },
        "Packaged Companion Host": {
            "jobs": ("Packaged Companion host evidence",),
            "artifacts": ("packaged-companion-host-{sha}",),
        },
    },
    "pull_request": {
        "Build & Test": {
            "jobs": BUILD_JOBS,
            "artifacts": (
                "alpha-0-android-instrumentation-{sha}",
                "block-d-operational-evidence-{sha}",
            ),
        },
        "Security": {
            "jobs": (
                "Secret and image scan",
                "Dependency audit",
                "CodeQL (python)",
                "CodeQL (javascript)",
            ),
            "artifacts": (),
        },
        "P1 Evidence": {
            "jobs": ("P1 evidence artifacts",),
            "artifacts": ("sentinel-p1-evidence-{sha}",),
        },
        "Packaged Companion Host": {
            "jobs": ("Packaged Companion host evidence",),
            "artifacts": ("packaged-companion-host-{sha}",),
        },
        "ALPHA-0 Android CI": {
            "jobs": ("Build Android APK",),
            "artifacts": ("alpha-0-debug-apk-{sha}",),
        },
    },
}


def canonical_digest(document: dict[str, Any]) -> str:
    payload = copy.deepcopy(document)
    payload.pop("evidenceDigest", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _api_get(url: str, token: str, timeout: float = 20.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "sentinel-release-evidence/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(8 * 1024 * 1024)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", "replace")
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API network error: {exc.reason}") from exc
    return json.loads(body)


def _runs_url(repo: str, sha: str, event: str) -> str:
    query = urllib.parse.urlencode({"head_sha": sha, "event": event, "per_page": 100})
    return f"https://api.github.com/repos/{repo}/actions/runs?{query}"


def _latest_runs(payload: dict[str, Any], names: set[str], sha: str, event: str) -> dict[str, dict[str, Any]]:
    chosen: dict[str, dict[str, Any]] = {}
    for run in payload.get("workflow_runs", []):
        name = run.get("name")
        if name not in names or run.get("head_sha") != sha or run.get("event") != event:
            continue
        previous = chosen.get(name)
        if previous is None or int(run.get("id", 0)) > int(previous.get("id", 0)):
            chosen[name] = run
    return chosen


def _successful_external_codeql(checks: dict[str, Any], sha: str) -> dict[str, Any] | None:
    candidates = []
    for check in checks.get("check_runs", []):
        app = check.get("app") or {}
        if (
            check.get("name") == "CodeQL"
            and check.get("head_sha") == sha
            and app.get("slug") == "github-advanced-security"
        ):
            candidates.append(check)
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: int(item.get("id", 0)))
    if latest.get("status") == "completed" and latest.get("conclusion") == "success":
        return latest
    return None


def _collect_once(repo: str, sha: str, event: str, token: str, version: str) -> tuple[dict[str, Any] | None, str]:
    specs = WORKFLOW_SPECS[event]
    payload = _api_get(_runs_url(repo, sha, event), token)
    runs = _latest_runs(payload, set(specs), sha, event)
    missing = sorted(set(specs) - set(runs))
    if missing:
        return None, "missing workflows: " + ", ".join(missing)

    for name, run in runs.items():
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return None, f"workflow {name!r} is {status!r}"
        if conclusion != "success":
            raise RuntimeError(f"workflow {name!r} completed with {conclusion!r}")

    external_checks: list[dict[str, Any]] = []
    if event == "pull_request":
        checks = _api_get(f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?per_page=100", token)
        codeql = _successful_external_codeql(checks, sha)
        if codeql is None:
            return None, "GitHub Advanced Security CodeQL check is not successful yet"
        external_checks.append(
            {
                "id": int(codeql["id"]),
                "name": "CodeQL",
                "appSlug": "github-advanced-security",
                "status": "completed",
                "conclusion": "success",
                "headSha": sha,
                "htmlUrl": codeql.get("html_url"),
            }
        )

    workflow_evidence: list[dict[str, Any]] = []
    for workflow_name in sorted(specs):
        run = runs[workflow_name]
        run_id = int(run["id"])
        jobs_payload = _api_get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?filter=latest&per_page=100", token)
        jobs_by_name = {job.get("name"): job for job in jobs_payload.get("jobs", [])}
        required_jobs = specs[workflow_name]["jobs"]
        missing_jobs = [name for name in required_jobs if name not in jobs_by_name]
        if missing_jobs:
            raise RuntimeError(f"workflow {workflow_name!r} missing required jobs: {', '.join(missing_jobs)}")
        job_evidence = []
        for job_name in sorted(required_jobs):
            job = jobs_by_name[job_name]
            if job.get("status") != "completed" or job.get("conclusion") != "success":
                raise RuntimeError(
                    f"workflow {workflow_name!r} job {job_name!r} is "
                    f"{job.get('status')!r}/{job.get('conclusion')!r}"
                )
            job_evidence.append(
                {
                    "id": int(job["id"]),
                    "name": job_name,
                    "status": "completed",
                    "conclusion": "success",
                }
            )

        artifacts_payload = _api_get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100", token)
        artifacts = artifacts_payload.get("artifacts", [])
        artifacts_by_name = {artifact.get("name"): artifact for artifact in artifacts}
        required_artifact_names = [template.format(sha=sha) for template in specs[workflow_name]["artifacts"]]
        missing_artifacts = [name for name in required_artifact_names if name not in artifacts_by_name]
        if missing_artifacts:
            raise RuntimeError(
                f"workflow {workflow_name!r} missing required artifacts: {', '.join(missing_artifacts)}"
            )
        artifact_evidence = []
        for artifact in sorted(artifacts, key=lambda item: str(item.get("name", ""))):
            name = artifact.get("name")
            digest = artifact.get("digest")
            workflow_run = artifact.get("workflow_run") or {}
            if artifact.get("expired"):
                raise RuntimeError(f"workflow {workflow_name!r} artifact {name!r} is expired")
            if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
                raise RuntimeError(f"workflow {workflow_name!r} artifact {name!r} lacks a SHA-256 digest")
            if workflow_run.get("head_sha") != sha:
                raise RuntimeError(f"workflow {workflow_name!r} artifact {name!r} is bound to a different SHA")
            size = int(artifact.get("size_in_bytes", 0))
            if size <= 0:
                raise RuntimeError(f"workflow {workflow_name!r} artifact {name!r} is empty")
            artifact_evidence.append(
                {
                    "id": int(artifact["id"]),
                    "name": name,
                    "sizeBytes": size,
                    "digest": digest,
                    "expired": False,
                    "headSha": sha,
                    "expiresAt": artifact.get("expires_at"),
                    "required": name in required_artifact_names,
                }
            )

        workflow_evidence.append(
            {
                "name": workflow_name,
                "runId": run_id,
                "runAttempt": int(run.get("run_attempt", 1)),
                "event": event,
                "headSha": sha,
                "status": "completed",
                "conclusion": "success",
                "htmlUrl": run.get("html_url"),
                "jobs": job_evidence,
                "artifacts": artifact_evidence,
            }
        )

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": {
            "repository": repo,
            "sha": sha,
            "version": version,
            "event": event,
        },
        "claims": {
            "signedReleaseArtifact": False,
            "releasePublished": False,
            "productionDeployed": False,
            "externalEnvironmentAcceptanceSatisfied": False,
        },
        "workflows": workflow_evidence,
        "externalChecks": external_checks,
    }
    manifest["evidenceDigest"] = canonical_digest(manifest)
    return manifest, "ready"


def collect(repo: str, sha: str, event: str, token: str, version: str, wait_seconds: int, poll_seconds: int) -> dict[str, Any]:
    if not REPO_RE.fullmatch(repo):
        raise ValueError("repository must be owner/name")
    if not SHA_RE.fullmatch(sha):
        raise ValueError("sha must be 40 lowercase hexadecimal characters")
    if event not in WORKFLOW_SPECS:
        raise ValueError("event must be push or pull_request")
    if not token:
        raise ValueError("GitHub token is required")
    if not version.strip():
        raise ValueError("version is empty")
    if wait_seconds < 0 or poll_seconds <= 0:
        raise ValueError("invalid wait/poll interval")

    deadline = time.monotonic() + wait_seconds
    last_reason = "not started"
    while True:
        manifest, reason = _collect_once(repo, sha, event, token, version.strip())
        if manifest is not None:
            return manifest
        last_reason = reason
        if time.monotonic() >= deadline:
            raise TimeoutError(f"release evidence preflight timed out: {last_reason}")
        print(f"waiting for exact-SHA evidence: {last_reason}", flush=True)
        time.sleep(poll_seconds)


def verify_manifest(
    manifest: dict[str, Any],
    *,
    expected_repository: str | None = None,
    expected_sha: str | None = None,
    expected_version: str | None = None,
) -> None:
    if manifest.get("schema") != SCHEMA or manifest.get("status") != "PASS":
        raise ValueError("invalid schema or non-PASS status")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValueError("missing source")
    repo = source.get("repository")
    sha = source.get("sha")
    version = source.get("version")
    event = source.get("event")
    if not isinstance(repo, str) or not REPO_RE.fullmatch(repo):
        raise ValueError("invalid source repository")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("invalid source sha")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("invalid source version")
    if event not in WORKFLOW_SPECS:
        raise ValueError("invalid source event")
    if expected_repository is not None and repo != expected_repository:
        raise ValueError("repository mismatch")
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("source SHA mismatch")
    if expected_version is not None and version != expected_version:
        raise ValueError("version mismatch")

    claims = manifest.get("claims")
    expected_claims = {
        "signedReleaseArtifact": False,
        "releasePublished": False,
        "productionDeployed": False,
        "externalEnvironmentAcceptanceSatisfied": False,
    }
    if claims != expected_claims:
        raise ValueError("release preflight must not claim signing/publication/deployment/external acceptance")

    workflows = manifest.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("workflows must be a list")
    by_name = {item.get("name"): item for item in workflows if isinstance(item, dict)}
    specs = WORKFLOW_SPECS[event]
    if set(by_name) != set(specs):
        raise ValueError("workflow evidence set mismatch")

    for workflow_name, spec in specs.items():
        item = by_name[workflow_name]
        if (
            item.get("event") != event
            or item.get("headSha") != sha
            or item.get("status") != "completed"
            or item.get("conclusion") != "success"
            or not isinstance(item.get("runId"), int)
            or item["runId"] <= 0
            or not isinstance(item.get("runAttempt"), int)
            or item["runAttempt"] <= 0
        ):
            raise ValueError(f"invalid workflow evidence for {workflow_name}")

        jobs = item.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError(f"jobs missing for {workflow_name}")
        jobs_by_name = {job.get("name"): job for job in jobs if isinstance(job, dict)}
        if set(jobs_by_name) != set(spec["jobs"]):
            raise ValueError(f"job evidence set mismatch for {workflow_name}")
        for job_name, job in jobs_by_name.items():
            if job.get("status") != "completed" or job.get("conclusion") != "success" or int(job.get("id", 0)) <= 0:
                raise ValueError(f"job {job_name} is not successful")

        artifacts = item.get("artifacts")
        if not isinstance(artifacts, list):
            raise ValueError(f"artifacts missing for {workflow_name}")
        artifact_names: set[str] = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ValueError("artifact entry must be an object")
            name = artifact.get("name")
            if not isinstance(name, str) or not name or name in artifact_names:
                raise ValueError("invalid or duplicate artifact name")
            artifact_names.add(name)
            if (
                artifact.get("expired") is not False
                or artifact.get("headSha") != sha
                or not isinstance(artifact.get("digest"), str)
                or not DIGEST_RE.fullmatch(artifact["digest"])
                or int(artifact.get("id", 0)) <= 0
                or int(artifact.get("sizeBytes", 0)) <= 0
            ):
                raise ValueError(f"invalid artifact evidence: {name}")
        required_names = {template.format(sha=sha) for template in spec["artifacts"]}
        if not required_names.issubset(artifact_names):
            raise ValueError(f"required artifact evidence missing for {workflow_name}")
        for artifact in artifacts:
            should_be_required = artifact["name"] in required_names
            if artifact.get("required") is not should_be_required:
                raise ValueError(f"artifact required flag mismatch: {artifact['name']}")

    external_checks = manifest.get("externalChecks")
    if not isinstance(external_checks, list):
        raise ValueError("externalChecks must be a list")
    if event == "pull_request":
        matches = [
            check
            for check in external_checks
            if isinstance(check, dict)
            and check.get("name") == "CodeQL"
            and check.get("appSlug") == "github-advanced-security"
            and check.get("headSha") == sha
            and check.get("status") == "completed"
            and check.get("conclusion") == "success"
            and int(check.get("id", 0)) > 0
        ]
        if len(matches) != 1:
            raise ValueError("exactly one successful GitHub Advanced Security CodeQL check is required")
    elif external_checks:
        raise ValueError("push evidence must not invent PR-only external checks")

    digest = manifest.get("evidenceDigest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise ValueError("invalid evidence digest")
    if digest != canonical_digest(manifest):
        raise ValueError("evidence digest mismatch")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--repository", required=True)
    collect_parser.add_argument("--sha", required=True)
    collect_parser.add_argument("--event", choices=sorted(WORKFLOW_SPECS), required=True)
    collect_parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    collect_parser.add_argument("--version-file", default="VERSION")
    collect_parser.add_argument("--output", required=True)
    collect_parser.add_argument("--wait-seconds", type=int, default=1200)
    collect_parser.add_argument("--poll-seconds", type=int, default=15)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--input", required=True)
    verify_parser.add_argument("--expected-repository")
    verify_parser.add_argument("--expected-sha")
    verify_parser.add_argument("--expected-version")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "collect":
            version = Path(args.version_file).read_text(encoding="utf-8").strip()
            manifest = collect(
                args.repository,
                args.sha,
                args.event,
                args.token,
                version,
                args.wait_seconds,
                args.poll_seconds,
            )
            verify_manifest(
                manifest,
                expected_repository=args.repository,
                expected_sha=args.sha,
                expected_version=version,
            )
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"release evidence PASS: {manifest['evidenceDigest']}")
        else:
            manifest = json.loads(Path(args.input).read_text(encoding="utf-8"))
            verify_manifest(
                manifest,
                expected_repository=args.expected_repository,
                expected_sha=args.expected_sha,
                expected_version=args.expected_version,
            )
            print(f"release evidence verified: {manifest['evidenceDigest']}")
    except (OSError, ValueError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"release evidence FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
