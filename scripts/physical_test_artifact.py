#!/usr/bin/env python3
"""Verify and describe the exact-SHA Android physical-test artifact."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


EXPECTED_APPLICATION_ID = "com.alpha0.app.physicaltest"
EXPECTED_VARIANT = "physicalTest"
EXPECTED_STAGING_ORIGIN = "https://sentinel-core-staging.onrender.com"
EXPECTED_HTTP_READ_TIMEOUT_MS = 75_000
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DEX_ENTRY = re.compile(r"^classes(?:\d+)?\.dex$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_staging_origin(raw: str) -> str:
    value = raw.strip().rstrip("/")
    parsed = urlsplit(value)
    require(parsed.scheme == "https", "physical-test API origin must use HTTPS")
    require(parsed.hostname is not None, "physical-test API origin must include a host")
    require(parsed.username is None and parsed.password is None, "physical-test API origin must not contain credentials")
    require(not parsed.path and not parsed.query and not parsed.fragment, "physical-test API origin must not contain path, query or fragment")
    try:
        require(not ipaddress.ip_address(parsed.hostname).is_loopback, "physical-test API origin must not be loopback")
    except ValueError:
        require(parsed.hostname.lower() not in {"localhost", "localhost.localdomain"}, "physical-test API origin must not be loopback")
    require(value == EXPECTED_STAGING_ORIGIN, "physical-test API origin must be the canonical staging Core")
    return value


def load_output_metadata(path: Path, apk: Path, canonical_version: str) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("artifactType", {}).get("type") == "APK", "Gradle output metadata must describe an APK")
    require(document.get("applicationId") == EXPECTED_APPLICATION_ID, "physical-test application ID mismatch")
    require(document.get("variantName") == EXPECTED_VARIANT, "physical-test variant mismatch")
    elements = document.get("elements")
    require(isinstance(elements, list) and len(elements) == 1, "physical-test build must contain exactly one APK output")
    element = elements[0]
    require(element.get("outputFile") == apk.name, "Gradle output metadata does not identify the selected APK")
    require(isinstance(element.get("versionCode"), int) and element["versionCode"] > 0, "physical-test versionCode must be positive")
    require(element.get("versionName") == f"{canonical_version}-physical-test", "physical-test versionName mismatch")
    return element


def inspect_apk(apk: Path, source_sha: str, api_base_url: str) -> None:
    require(apk.is_file(), "physical-test APK is missing")
    with zipfile.ZipFile(apk) as archive:
        dex_names = sorted(name for name in archive.namelist() if DEX_ENTRY.fullmatch(name))
        require(bool(dex_names), "physical-test APK contains no classes*.dex")
        dex = b"".join(archive.read(name) for name in dex_names)
    for expected in (source_sha, api_base_url, "FORENSIC_TEST"):
        require(expected.encode("utf-8") in dex, f"compiled APK is missing expected identity: {expected}")
    for forbidden in (b"http://127.0.0.1", b"https://127.0.0.1", b"http://localhost", b"https://localhost", b"10.0.2.2"):
        require(forbidden not in dex, f"compiled APK contains forbidden loopback endpoint: {forbidden.decode()}")


def build_manifest(
    *,
    apk: Path,
    output_metadata: Path,
    version_file: Path,
    source_sha: str,
    api_base_url: str,
    repository: str,
    run_id: str,
    run_attempt: str,
    signer_sha256: str,
    expected_signer_sha256: str | None = None,
    signing_mode: str = "ephemeral-debug",
    workflow_name: str = "Physical Test APK",
    generated_at: str | None = None,
) -> dict[str, object]:
    require(SHA40.fullmatch(source_sha) is not None, "source SHA must be 40-character lowercase hex")
    require(repository == "spenskoj90-sudo/alpha-0", "physical-test artifact repository mismatch")
    require(run_id.isdigit() and int(run_id) > 0, "workflow run ID must be a positive integer")
    require(run_attempt.isdigit() and int(run_attempt) > 0, "workflow run attempt must be a positive integer")
    require(signing_mode in {"stable-test", "ephemeral-debug"}, "invalid physical-test signing mode")
    require(workflow_name in {"Physical Test APK", "Physical Test Update APK"}, "invalid physical-test workflow name")
    require(
        (signing_mode == "stable-test") == (workflow_name == "Physical Test Update APK"),
        "stable-test signing must use the dedicated update workflow",
    )
    signer = signer_sha256.strip().lower()
    require(SHA256.fullmatch(signer) is not None, "signer certificate SHA-256 must be 64-character lowercase hex")
    expected_signer = expected_signer_sha256.strip().lower() if expected_signer_sha256 is not None else None
    if signing_mode == "stable-test":
        require(expected_signer is not None, "stable-test signing requires a pinned expected signer certificate SHA-256")
        require(SHA256.fullmatch(expected_signer) is not None, "expected signer certificate SHA-256 must be 64-character lowercase hex")
        require(signer == expected_signer, "physical-test signer certificate does not match pinned update lineage")
    else:
        require(expected_signer is None, "ephemeral-debug artifacts must not claim a pinned update signer lineage")
    origin = validate_staging_origin(api_base_url)
    canonical_version = version_file.read_text(encoding="utf-8").strip()
    require(bool(canonical_version), "canonical VERSION is empty")
    metadata = load_output_metadata(output_metadata, apk, canonical_version)
    inspect_apk(apk, source_sha, origin)
    apk_bytes = apk.read_bytes()
    timestamp = generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "schema": "sentinel.android-physical-test-artifact.v1",
        "repository": repository,
        "sourceSha": source_sha,
        "workflow": {
            "name": workflow_name,
            "runId": int(run_id),
            "runAttempt": int(run_attempt),
        },
        "artifactName": (
            f"sentinel-physical-test-update-apk-{source_sha}"
            if signing_mode == "stable-test"
            else f"sentinel-physical-test-apk-{source_sha}"
        ),
        "apk": {
            "fileName": apk.name,
            "sha256": hashlib.sha256(apk_bytes).hexdigest(),
            "sizeBytes": len(apk_bytes),
            "applicationId": EXPECTED_APPLICATION_ID,
            "versionName": metadata["versionName"],
            "versionCode": metadata["versionCode"],
            "buildVariant": EXPECTED_VARIANT,
            "debuggable": True,
            "minified": False,
        },
        "apiEnvironment": "staging",
        "apiBaseUrl": origin,
        "runtimeEnvironment": "staging",
        "signingMode": signing_mode,
        "signerCertificateSha256": signer,
        "signerLineageVerified": signing_mode == "stable-test",
        "updateCompatible": signing_mode == "stable-test",
        "httpReadTimeoutMs": EXPECTED_HTTP_READ_TIMEOUT_MS,
        "coldStartAware": True,
        "diagnosticsMode": "FORENSIC_TEST",
        "generatedAt": timestamp,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--output-metadata", type=Path, required=True)
    parser.add_argument("--version-file", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--signer-sha256", required=True)
    parser.add_argument("--expected-signer-sha256")
    parser.add_argument("--signing-mode", default="ephemeral-debug")
    parser.add_argument("--workflow-name", default="Physical Test APK")
    parser.add_argument("--generated-at")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_manifest(
            apk=args.apk,
            output_metadata=args.output_metadata,
            version_file=args.version_file,
            source_sha=args.source_sha,
            api_base_url=args.api_base_url,
            repository=args.repository,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            signer_sha256=args.signer_sha256,
            expected_signer_sha256=args.expected_signer_sha256,
            signing_mode=args.signing_mode,
            workflow_name=args.workflow_name,
            generated_at=args.generated_at,
        )
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"physical-test artifact verification failed: {error}", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
