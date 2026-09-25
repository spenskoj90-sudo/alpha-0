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

    exact_pr_checkout_ref = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"
    pull_request_workflows = (
        "android-build.yml",
        "build.yml",
        "p1-evidence.yml",
        "packaged-companion.yml",
        "physical-test-apk.yml",
        "release-evidence.yml",
        "security.yml",
        "supply-chain-evidence.yml",
    )
    for name in pull_request_workflows:
        text = workflow_text[name]
        checkout_count = text.count("uses: actions/checkout@")
        exact_ref_count = text.count(exact_pr_checkout_ref)
        checks.require(checkout_count > 0, f"{name} contains a source checkout")
        checks.require(
            exact_ref_count == checkout_count,
            f"{name} binds every checkout to exact PR head / push SHA",
        )

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
    checks.require("source_sha:" in candidate, "release-candidate requires an explicit exact source SHA")
    checks.require("needs: presecret" in candidate, "release signing depends on the pre-secret evidence gate")
    try:
        candidate_presecret = candidate.split("  presecret:", 1)[1].split("  release-candidate:", 1)[0]
        candidate_signing = candidate.split("  release-candidate:", 1)[1]
    except IndexError:
        candidate_presecret = ""
        candidate_signing = ""
    checks.require(bool(candidate_presecret), "release-candidate has a distinct pre-secret job")
    checks.require("secrets." not in candidate_presecret, "release-candidate pre-secret job references no repository secrets")
    checks.require("release_lineage.py presecret" in candidate_presecret, "release-candidate pre-secret job verifies canonical main evidence")
    checks.require("ANDROID_KEYSTORE_BASE64" in candidate_signing, "release-candidate signing material is confined to the dependent signing job")
    checks.require(
        candidate_signing.find("Reconfirm canonical evidence before secret access")
        < candidate_signing.find("Decode release keystore")
        and candidate_signing.find("Reconfirm canonical evidence before secret access") >= 0,
        "release-candidate reconfirms evidence before first signing-secret access",
    )

    release = workflow_text["release.yml"]
    checks.require('tags: ["v*.*.*"]' in release, "release publication is version-tag scoped")
    checks.require("verify release tag version" in release.lower(), "release tag is checked against VERSION")
    checks.require("ANDROID_KEYSTORE_BASE64" not in release and "assembleRelease" not in release, "tag publication never re-signs the Android APK")
    checks.require("  verify-candidate:" in release and "  publish:" in release, "release separates candidate verification from publication authority")
    try:
        release_presecret = release.split("  presecret:", 1)[1].split("  verify-candidate:", 1)[0]
        release_verify = release.split("  verify-candidate:", 1)[1].split("  publish:", 1)[0]
        release_publish = release.split("  publish:", 1)[1]
    except IndexError:
        release_presecret = ""
        release_verify = ""
        release_publish = ""
    checks.require("contents: write" not in release_presecret + release_verify, "release preflight/candidate verification have no publication authority")
    checks.require("secrets." not in release_presecret + release_verify, "release preflight/candidate verification reference no repository secrets")
    checks.require("release_lineage.py fetch-candidate" in release_verify, "read-only release job verifies the signed candidate lineage")
    checks.require("contents: write" in release_publish, "only final release publication job receives contents write authority")
    checks.require("release_lineage.py" not in release_publish and "actions/checkout@" not in release_publish, "publication-authority job executes no repository code")
    checks.require("actions/download-artifact@" in release_publish, "publication-authority job consumes only preverified workflow artifact input")

    build = workflow_text["build.yml"]
    checks.require(
        "--cov-fail-under=85" in build,
        "non-PostgreSQL Core line coverage gate is at least 85%",
    )
    checks.require(
        "--cov-branch" in build and "line_min = 90.0" in build and "branch_min = 85.0" in build,
        "combined Core coverage measures branches and enforces 90% lines / 85% branches",
    )
    checks.require(
        "if line_pct < line_min or branch_pct < branch_min:" in build
        and "COMBINED_COVERAGE_GATE_FAILED" in build,
        "combined Core coverage gate fails closed below either threshold",
    )

    security = workflow_text["security.yml"]
    checks.require("ignore-unfixed: false" in security, "Trivy includes unfixed HIGH/CRITICAL findings")
    checks.require("severity: HIGH,CRITICAL" in security and "exit-code: 1" in security, "Trivy HIGH/CRITICAL gate fails closed")

    branch_hygiene = workflow_text["branch-hygiene.yml"]
    checks.require(
        "contents: write" in branch_hygiene and "pull-requests: read" in branch_hygiene,
        "branch hygiene has only the authority needed for exact-ref deletion and PR verification",
    )
    checks.require(
        '"docs/BRANCH_INVENTORY.md"' in branch_hygiene
        and '{"MERGED_EXACT", "PURE_BEHIND", "CONTENT_SUPERSEDED"}' in branch_hygiene,
        "branch hygiene consumes only the active reconciled inventory classifications",
    )
    checks.require(
        'if [ "$remote_sha" != "$expected_sha" ]' in branch_hygiene
        and "ref mutation detected" in branch_hygiene
        and 'git fetch --no-tags origin "refs/heads/$branch"' in branch_hygiene
        and 'if [ "$fetched_sha" != "$expected_sha" ]' in branch_hygiene
        and 'protected="$(gh api' in branch_hygiene,
        "branch hygiene revalidates exact live and fetched tips and refuses protected refs",
    )
    checks.require(
        "exact PR-head mismatch" in branch_hygiene
        and 'merge_sha" = "$GITHUB_SHA' in branch_hygiene
        and 'head_repo" = "$GITHUB_REPOSITORY' in branch_hygiene,
        "branch hygiene binds merged and self-cleanup deletion to exact same-repository PR lineage",
    )


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
    checks.require("npm run test:coverage" in build, "Web build enforces measured API/server coverage")
    checks.require("npm ci" in p1 and "npm ci" in security, "security/evidence workflows use npm ci")

    checks.require(
        package.get("devDependencies", {}).get("@vitest/coverage-v8") == "5.0.1",
        "Web pins the Vitest V8 coverage provider to the Vitest release line",
    )
    checks.require(
        package.get("scripts", {}).get("test:coverage") == "vitest run --coverage",
        "Web exposes the deterministic coverage entrypoint",
    )
    vitest = read("web/vitest.config.mts")
    checks.require(
        "include: ['app/api/**/*.ts']" in vitest
        and "statements: 85" in vitest
        and "lines: 85" in vitest
        and "functions: 85" in vitest
        and "branches: 80" in vitest,
        "Web API/server coverage hard-gates 85% statements/lines/functions and 80% branches",
    )
    checks.require(
        "'app/api/_lib/core-session.ts'" in vitest
        and "'app/api/session/**/*.ts'" in vitest
        and "'app/api/billing/**/*.ts'" in vitest
        and "branches: 85" in vitest
        and "lines: 90" in vitest,
        "Web critical auth/session/billing coverage has a 90% line/function and 85% branch floor",
    )


def check_versions(checks: Checks) -> None:
    canonical = read("VERSION").strip().lower()
    checks.require(bool(SEMVER_RC.fullmatch(canonical)), "VERSION uses canonical release-candidate SemVer")

    package = json.loads(read("web/package.json"))["version"].lower()
    pyproject = read("server/pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    python_version = normalize_python_version(match.group(1)) if match else ""
    android = read("app/build.gradle.kts")
    main = read("server/app/main.py")

    checks.require(package == canonical, "web version matches VERSION")
    checks.require(python_version == canonical, "Core package version matches VERSION")
    checks.require(read(".node-version").strip() == "24.21.0", "Node runtime is pinned to 24.21.0 LTS")
    checks.require(read(".python-version").strip() == "3.14.7", "Python runtime is pinned to 3.14.7")
    web_package = json.loads(read("web/package.json"))
    checks.require(web_package.get("engines", {}).get("node") == "24.x", "Web declares Node 24 LTS")
    checks.require(web_package.get("dependencies", {}).get("next") == "16.3.6", "Web pins Next.js 16.3.6")
    checks.require(web_package.get("dependencies", {}).get("react") == "19.3.0", "Web pins React 19.3.0")
    checks.require(web_package.get("devDependencies", {}).get("typescript") == "6.0.3", "Web pins TypeScript 6.0.3")
    checks.require(web_package.get("devDependencies", {}).get("eslint") == "9.39.5", "Web uses Next-compatible ESLint 9.39.5")
    checks.require("node:24.21.0-alpine3.24@sha256:" in read("web/Dockerfile"), "Web image pins Node 24.21.0 by digest")
    checks.require("python:3.14.7-slim@sha256:" in read("server/Dockerfile"), "Core image pins Python 3.14.7 by digest")
    launcher = json.loads(read("launcher/package.json"))
    checks.require(launcher.get("engines", {}).get("node") == "24.x", "Launcher declares Node 24 LTS")
    checks.require(launcher.get("dependencies", {}).get("electron") == "44.4.5", "Launcher pins Electron 44.4.5")
    checks.require(launcher.get("sentinelPackaging", {}).get("electronVersion") == "44.4.5", "Launcher packaging pins Electron 44.4.5")
    checks.require('implementation("io.sentry:sentry-android:8.57.0")' in android, "Android pins Sentry 8.57.0")
    checks.require('implementation("androidx.navigation:navigation-compose:2.10.2")' in android, "Android pins Navigation Compose 2.10.2")
    checks.require('"httpx2==2.13.1"' in pyproject, "Core test tooling pins httpx2 2.13.1")
    checks.require('"sqlalchemy==2.0.54"' in pyproject, "Core retains validated SQLAlchemy 2.0.54 RC line")
    checks.require('androidTestImplementation("androidx.test.ext:junit:1.3.0")' in android, "Android test JUnit is current stable")
    checks.require('androidTestImplementation("androidx.test:runner:1.7.0")' in android, "Android test runner is current stable")
    checks.require('androidTestImplementation("androidx.test.espresso:espresso-core:3.7.0")' in android, "Android Espresso is current stable")
    checks.require("from app.version import APP_VERSION" in main, "API runtime version uses canonical resolver")
    version_module = read("server/app/version.py")
    checks.require('Path(__file__).resolve().parents[2] / "VERSION"' in version_module, "source runtime version reads VERSION")
    checks.require('distribution_version(_PACKAGE_NAME)' in version_module, "installed runtime version uses package metadata")
    checks.require(
        'versionName = rootProject.file("VERSION").readText().trim()' in android,
        "Android versionName reads VERSION",
    )
    canonical_version_code = re.search(r"^val canonicalVersionCode\s*=\s*(\d+)\s*$", android, re.MULTILINE)
    checks.require(
        bool(canonical_version_code and int(canonical_version_code.group(1)) > 0),
        "Android canonical versionCode is positive and explicit",
    )
    checks.require(
        "versionCode = if (physicalTestRequested) physicalTestVersionCode else canonicalVersionCode" in android,
        "Android versionCode selects canonical or physical-test identity explicitly",
    )
    checks.require(
        'providers.environmentVariable("SENTINEL_PHYSICAL_TEST_VERSION_CODE")' in android
        and "physicalTestVersionCodeRaw.toIntOrNull()" in android
        and "if (physicalTestVersionCode <= 0)" in android,
        "Android physical-test versionCode override rejects missing/non-positive identity",
    )
    for workflow_name in ("physical-test-apk.yml", "physical-test-update-apk.yml"):
        workflow = read(f".github/workflows/{workflow_name}")
        checks.require(
            "value=$((100000000 + GITHUB_RUN_NUMBER))" in workflow
            and 'SENTINEL_PHYSICAL_TEST_VERSION_CODE=$value' in workflow,
            f"{workflow_name} derives monotonic physical-test versionCode from GitHub run number",
        )

    physical_routine = read(".github/workflows/physical-test-apk.yml")
    physical_update = read(".github/workflows/physical-test-update-apk.yml")
    checks.require(
        '--signer-sha256 "$SENTINEL_PHYSICAL_TEST_SIGNER_SHA256"' in physical_routine
        and "physical-test-signer.txt" in physical_routine,
        "routine physical-test artifact retains signer identity evidence",
    )
    checks.require(
        "vars.PHYSICAL_TEST_SIGNER_SHA256" in physical_update
        and '--expected-signer-sha256 "$PHYSICAL_TEST_EXPECTED_SIGNER_SHA256"' in physical_update
        and '--signer-sha256 "$SENTINEL_PHYSICAL_TEST_SIGNER_SHA256"' in physical_update,
        "stable physical-test update requires pinned signer continuity evidence",
    )

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
        "docs/BRANCH_DELETION_MANIFEST_2026-09-23.md": "Status:** HISTORICAL EVIDENCE RECORD",
    }
    for path, marker in required_status.items():
        checks.require(marker in read(path).splitlines()[0:8].__str__(), f"{path} has explicit {marker} banner")

    current_state = read("docs/SENTINEL_CURRENT_STATE.md")
    checks.require(not re.search(r"\b[0-9a-f]{40}\b", current_state), "current-state guide does not embed a mutable commit SHA")
    deployment = read("docs/DEPLOYMENT.md")
    checks.require(
        "current **pre-release/staging** database is hosted on Neon PostgreSQL" in deployment
        and "Supabase (managed PostgreSQL" not in deployment,
        "active deployment guide matches the Neon managed-database boundary",
    )
    tasks = read("docs/TASKS.md")
    checks.require(
        "REPOSITORY HYGIENE AUTHORIZED" in tasks
        and "remote deletion still Owner-only" not in tasks
        and "OWNER GATE:** branch deletion" not in tasks,
        "task board matches evidence-gated autonomous branch hygiene authorization",
    )

    branch_inventory = read("docs/BRANCH_INVENTORY.md")
    checks.require(
        "**Status:** ACTIVE" in branch_inventory
        and "CONTENT_SUPERSEDED" in branch_inventory
        and "MERGED_EXACT" in branch_inventory,
        "active branch inventory records evidence-gated cleanup classifications",
    )
    checks.require(
        "| UNIQUE_RECONCILE |" not in branch_inventory
        and "| UNKNOWN |" not in branch_inventory,
        "active branch inventory leaves no unresolved or unknown historical branch state",
    )
    checks.require(
        "BRANCH_HYGIENE deleted=40 already_absent=0" in branch_inventory
        and "| `main` | ACTIVE |" in branch_inventory
        and "only protected `main`" in branch_inventory,
        "active branch inventory records completed exact-tip cleanup and compact durable state",
    )
    historical_branch_manifest = read("docs/BRANCH_DELETION_MANIFEST_2026-09-23.md")
    checks.require(
        "HISTORICAL EVIDENCE RECORD" in historical_branch_manifest
        and "Owner-only irreversible gate" not in historical_branch_manifest,
        "dated branch manifest is historical evidence, not live deletion authority",
    )

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
    provider_matrix = read("docs/PROVIDER_STATUS_MATRIX.md")
    checks.require(
        "**Status:** ACTIVE" in provider_matrix
        and "Stripe Billing" in provider_matrix
        and "Resend email" in provider_matrix
        and "Sentry Android" in provider_matrix
        and "PostHog operational telemetry" in provider_matrix
        and "Google federated auth" in provider_matrix
        and "Telegram federated auth" in provider_matrix
        and "VK federated auth" in provider_matrix
        and "STT provider boundary" in provider_matrix
        and "TTS provider boundary" in provider_matrix,
        "provider status matrix covers every required external provider boundary",
    )
    checks.require(
        "| PostHog operational telemetry | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | MISSING |" in provider_matrix
        and "Production delivery is `MISSING` **by design**" in provider_matrix,
        "provider matrix does not misstate production PostHog as an activated or merely credential-gated path",
    )
    platform = read("docs/PLATFORM_MODERNIZATION_2026Q3.md")
    checks.require(
        "| Navigation Compose | 2.10.2 |" in platform
        and "httpx2 2.13.1" in platform
        and "**TypeScript 7.0.2:**" in platform
        and "**SQLAlchemy 2.1.0:**" in platform
        and "**Next.js 16.3.7:**" in platform,
        "platform baseline records final upstream recheck and explicit RC compatibility holds",
    )
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
