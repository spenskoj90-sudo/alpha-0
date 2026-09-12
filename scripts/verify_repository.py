#!/usr/bin/env python3
"""Fail-closed repository policy checks used by local validation and CI."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RC = re.compile(r"^(\d+)\.(\d+)\.(\d+)-rc(\d+)$")


class Checks:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes = 0

    def require(self, condition: bool, message: str) -> None:
        if condition:
            self.passes += 1
            print(f"PASS  {message}")
        else:
            self.failures.append(message)
            print(f"FAIL  {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def normalize_python_version(version: str) -> str:
    return re.sub(r"(?<=\d)rc(?=\d+$)", "-rc", version.lower())


def action_references() -> list[tuple[Path, int, str, str]]:
    references: list[tuple[Path, int, str, str]] = []
    pattern = re.compile(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)(?:\s+#\s*(.+))?$")
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1):
            match = pattern.match(line)
            if match:
                references.append((workflow, number, match.group(1), match.group(2) or ""))
    return references


def check_actions(checks: Checks) -> None:
    refs = action_references()
    checks.require(bool(refs), "workflow Action references discovered")
    for workflow, number, reference, comment in refs:
        label = f"{workflow.relative_to(ROOT)}:{number} immutable Action reference"
        if reference.startswith("./"):
            checks.require(True, label)
            continue
        if reference.startswith("docker://"):
            pinned = bool(re.search(r"@sha256:[0-9a-f]{64}$", reference))
        else:
            _, separator, revision = reference.rpartition("@")
            pinned = bool(separator and SHA40.fullmatch(revision))
        checks.require(pinned, label)
        checks.require(bool(comment.strip()), f"{workflow.relative_to(ROOT)}:{number} Action pin has readable version comment")


def check_workflow_boundaries(checks: Checks) -> None:
    workflow_text = {
        path.name: path.read_text(encoding="utf-8") for path in sorted(WORKFLOWS.glob("*.yml"))
    }
    for name, text in workflow_text.items():
        checks.require("permissions:" in text, f"{name} declares least-privilege permissions")

    routine = ("build.yml", "android-build.yml", "p1-evidence.yml", "security.yml")
    forbidden = ("secrets.ANDROID_KEY", "assembleRelease", "sentinel-release.jks")
    for name in routine:
        text = workflow_text[name]
        checks.require(
            not any(value in text for value in forbidden),
            f"{name} does not access release-signing material",
        )

    candidate = workflow_text["release-candidate.yml"]
    checks.require("workflow_dispatch:" in candidate, "release-candidate workflow is manual")
    checks.require("pull_request:" not in candidate and "branches:" not in candidate, "release-candidate workflow is not routine branch CI")

    release = workflow_text["release.yml"]
    checks.require('tags: ["v*.*.*"]' in release, "release publication is version-tag scoped")
    checks.require("Verify release tag matches canonical version" in release, "release tag is checked against VERSION")

    security = workflow_text["security.yml"]
    checks.require("ignore-unfixed: false" in security, "Trivy includes unfixed HIGH/CRITICAL findings")
    checks.require("severity: HIGH,CRITICAL" in security and "exit-code: 1" in security, "Trivy HIGH/CRITICAL gate fails closed")


def check_web(checks: Checks) -> None:
    package = json.loads(read("web/package.json"))
    lock = json.loads(read("web/package-lock.json"))
    root_lock = lock.get("packages", {}).get("", {})
    checks.require(lock.get("lockfileVersion", 0) >= 3, "npm lockfile format is deterministic")
    checks.require(lock.get("version") == package.get("version"), "npm package and lockfile versions agree")
    checks.require(root_lock.get("dependencies") == package.get("dependencies"), "npm locked runtime dependency declarations agree")
    checks.require(root_lock.get("devDependencies") == package.get("devDependencies"), "npm locked development dependency declarations agree")

    build = read(".github/workflows/build.yml")
    p1 = read(".github/workflows/p1-evidence.yml")
    security = read(".github/workflows/security.yml")
    checks.require("npm install" not in build + p1 + security, "validation workflows do not resolve web dependencies with npm install")
    checks.require("npm ci" in build and "npm test" in build, "Web build gates deterministic install and Vitest")
    checks.require("npm ci" in p1 and "npm ci" in security, "security/evidence workflows use npm ci")


def check_versions(checks: Checks) -> None:
    canonical = read("VERSION").strip().lower()
    checks.require(bool(SEMVER_RC.fullmatch(canonical)), "VERSION uses canonical release-candidate SemVer")

    package = json.loads(read("web/package.json"))["version"].lower()
    pyproject = read("server/pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    python_version = normalize_python_version(match.group(1)) if match else ""
    android = read("app/build.gradle.kts")

    checks.require(package == canonical, "web version matches VERSION")
    checks.require(python_version == canonical, "Core package version matches VERSION")
    checks.require(
        'versionName = rootProject.file("VERSION").readText().trim()' in android,
        "Android versionName reads VERSION",
    )
    version_code = re.search(r"versionCode\s*=\s*(\d+)", android)
    checks.require(bool(version_code and int(version_code.group(1)) > 0), "Android versionCode is positive and explicit")

    wrapper = read("gradle/wrapper/gradle-wrapper.properties")
    checksum = re.search(r"^distributionSha256Sum=([0-9a-f]{64})$", wrapper, re.MULTILINE)
    checks.require(bool(checksum), "Gradle distribution has an explicit SHA-256 checksum")
    checks.require(
        bool(checksum and checksum.group(1) in read("gradlew")),
        "Gradle bootstrap verifies the configured distribution checksum",
    )


def check_governance(checks: Checks) -> None:
    required_status = {
        "HANDOVER_DOCUMENT.md": "Status: HISTORICAL",
        "docs/API_REFERENCE.md": "Status: SUPERSEDED",
        "docs/AUDIT_CLOSURE_2026-08-13.md": "Status: HISTORICAL",
        "docs/PLATFORM_RC.md": "Status: SUPERSEDED",
        "docs/PROJECT_STATE.md": "Status: SUPERSEDED",
        "docs/SENTINEL_AUDIT_2026-08-25.md": "Status: HISTORICAL",
        "docs/SENTINEL_FINAL_AUDIT_2026-08-26.md": "Status: HISTORICAL",
        "docs/SENTINEL_SECURITY_BOUNDARY_AUDIT_ISSUE9.md": "Status: HISTORICAL",
    }
    for path, marker in required_status.items():
        checks.require(marker in read(path).splitlines()[0:8].__str__(), f"{path} has explicit {marker} banner")

    current_state = read("docs/SENTINEL_CURRENT_STATE.md")
    checks.require(not re.search(r"\b[0-9a-f]{40}\b", current_state), "current-state guide does not embed a mutable commit SHA")

    canonical = read("docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md")
    workflow = read("docs/WORKFLOW_CONTRACT.md")
    checks.require("only AI" in canonical and "No other AI" in canonical, "canonical governance remains GPT-only")
    checks.require(
        "exact PR HEAD SHA" in canonical
        and ("authorized to merge" in canonical or "may merge" in canonical),
        "canonical governance retains exact-SHA merge authority",
    )
    checks.require("sole AI engineering participant" in workflow, "workflow contract remains GPT-only")
    checks.require("DOCUMENT_STATUS.md" in read("README.md") or (ROOT / "docs/DOCUMENT_STATUS.md").exists(), "document authority map exists")
    checks.require((ROOT / "docs/REMOTE_BRANCH_CLEANUP_2026-09-12.md").exists(), "remote branch cleanup classification exists")


def main() -> int:
    checks = Checks()
    check_actions(checks)
    check_workflow_boundaries(checks)
    check_web(checks)
    check_versions(checks)
    check_governance(checks)
    print(f"\nPOLICY_PASSED={checks.passes} POLICY_FAILED={len(checks.failures)}")
    if checks.failures:
        print("Repository policy violations:")
        for failure in checks.failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
