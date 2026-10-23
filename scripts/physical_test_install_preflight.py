#!/usr/bin/env python3
"""Offline read-only APK upgrade preflight using an opt-in Owner diagnostic export.

An eligible result permits *further device-side verification*, not installation
or a claim that an independently authenticated APK signer has been verified.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

APP_ID = "com.alpha0.app.physicaltest"
SHA256 = re.compile(r"[0-9a-f]{64}")
SHA40 = re.compile(r"[0-9a-f]{40}")
MAX_DIAGNOSTICS_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 32 * 1024
MAX_APK_BYTES = 256 * 1024 * 1024
APK_IN_ARTIFACT = "app/build/outputs/apk/physicalTest/app-physicalTest.apk"
MANIFEST_IN_ARTIFACT = "physical-test-manifest.json"


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def evidence_from_diagnostics(archive: Path) -> tuple[int, str]:
    with gzip.open(archive, "rb") as stream:
        raw = stream.read(MAX_DIAGNOSTICS_BYTES + 1)
    require(len(raw) <= MAX_DIAGNOSTICS_BYTES, "DIAGNOSTICS_TOO_LARGE")
    starts, signers = [], []
    for line in raw.splitlines():
        require(len(line) <= 128 * 1024, "DIAGNOSTIC_LINE_TOO_LARGE")
        event = json.loads(line)
        require(type(event) is dict, "INVALID_DIAGNOSTIC_EVENT")
        if event.get("event") == "PROCESS_START":
            starts.append(event.get("details"))
        elif event.get("event") == "PACKAGE_SIGNER":
            signers.append(event.get("details"))
    require(len(starts) == len(signers) == 1, "AMBIGUOUS_INSTALLED_IDENTITY")
    start, signer = starts[0], signers[0]
    require(type(start) is dict and type(signer) is dict, "INVALID_INSTALLED_IDENTITY")
    require(start.get("package_name") == APP_ID and signer.get("package_name") == APP_ID, "PACKAGE_MISMATCH")
    require(start.get("build_type") == "physicalTest", "NOT_PHYSICAL_TEST_BUILD")
    version = start.get("version_code")
    require(type(version) is int and 1 <= version <= 2_100_000_000, "INVALID_INSTALLED_VERSION")
    require(signer.get("installed_version_code") == version, "INSTALLED_VERSION_DISAGREEMENT")
    require(signer.get("signer_count") == 1 and signer.get("multiple_signers") is False, "AMBIGUOUS_INSTALLED_SIGNER")
    digest = signer.get("signer_cert_sha256")
    require(type(digest) is str and SHA256.fullmatch(digest) is not None, "INVALID_INSTALLED_SIGNER")
    return version, digest


def evidence_from_artifact(archive: Path) -> tuple[dict, str]:
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        require(len(names) == len(set(names)), "DUPLICATE_ARTIFACT_ENTRIES")
        require(names.count(MANIFEST_IN_ARTIFACT) == names.count(APK_IN_ARTIFACT) == 1, "ARTIFACT_FILES_MISSING")
        manifest_info = zipped.getinfo(MANIFEST_IN_ARTIFACT)
        apk_info = zipped.getinfo(APK_IN_ARTIFACT)
        require(manifest_info.file_size <= MAX_MANIFEST_BYTES, "MANIFEST_TOO_LARGE")
        require(0 < apk_info.file_size <= MAX_APK_BYTES, "APK_SIZE_INVALID")
        manifest = json.loads(zipped.read(MANIFEST_IN_ARTIFACT))
        require(type(manifest) is dict, "INVALID_MANIFEST")
        identity = manifest.get("apk")
        require(type(identity) is dict and identity.get("applicationId") == APP_ID, "PACKAGE_MISMATCH")
        require(identity.get("buildVariant") == "physicalTest", "NOT_PHYSICAL_TEST_BUILD")
        require(manifest.get("schema") == "sentinel.android-physical-test-artifact.v1", "UNKNOWN_MANIFEST_SCHEMA")
        require(
            manifest.get("apiEnvironment") == "staging"
            and manifest.get("runtimeEnvironment") == "staging"
            and manifest.get("apiBaseUrl") == "https://sentinel-core-staging.onrender.com"
            and manifest.get("apiFallbackBaseUrl") == "https://sentinel-web-staging-fxhn.onrender.com/api/mobile-core",
            "UNEXPECTED_APK_ENVIRONMENT",
        )
        require(
            type(manifest.get("sourceSha")) is str
            and SHA40.fullmatch(manifest["sourceSha"]) is not None,
            "INVALID_SOURCE_SHA",
        )
        expected_hash = identity.get("sha256")
        require(type(expected_hash) is str and SHA256.fullmatch(expected_hash) is not None, "INVALID_APK_DIGEST")
        require(identity.get("sizeBytes") == apk_info.file_size, "APK_SIZE_MISMATCH")
        apk_hash = hashlib.sha256()
        with zipped.open(apk_info) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                apk_hash.update(chunk)
        require(apk_hash.hexdigest() == expected_hash, "APK_DIGEST_MISMATCH")
        signer = manifest.get("signerCertificateSha256")
        require(type(signer) is str and SHA256.fullmatch(signer) is not None, "INVALID_CANDIDATE_SIGNER")
        return manifest, signer


def assess(installed_version: int, installed_signer: str, manifest: dict, candidate_signer: str) -> dict:
    version = manifest["apk"].get("versionCode")
    require(type(version) is int and 1 <= version <= 2_100_000_000, "INVALID_CANDIDATE_VERSION")
    require(manifest.get("apiEnvironment") == "staging", "UNEXPECTED_APK_ENVIRONMENT")
    result = {
        "schema": "sentinel.physical-test-install-preflight.v1",
        "status": "BLOCKED",
        "reason": None,
        "installedVersionCode": installed_version,
        "candidateVersionCode": version,
        "installedSignerSha256": installed_signer,
        "candidateSignerSha256": candidate_signer,
        "candidateSourceSha": manifest["sourceSha"],
        "noDeviceOrSigningOperationPerformed": True,
        "apkSignerIndependentlyVerified": False,
    }
    if installed_signer != candidate_signer:
        result["reason"] = "SIGNER_MISMATCH"
    elif version <= installed_version:
        result["reason"] = "VERSION_NOT_HIGHER"
    elif (
        manifest.get("signingMode") != "stable-test"
        or manifest.get("signerLineageVerified") is not True
        or manifest.get("updateCompatible") is not True
    ):
        result["reason"] = "UPDATE_LINEAGE_NOT_VERIFIED"
    elif (
        type(manifest.get("updateBaselineVersionCode")) is not int
        or manifest["updateBaselineVersionCode"] < installed_version
    ):
        result["reason"] = "UPDATE_BASELINE_NOT_PROVEN"
    else:
        result["status"] = "ELIGIBLE_FOR_OWNER_DEVICE_CONFIRMATION"
        result["reason"] = "NO_CONFLICT_IN_SUPPLIED_EVIDENCE"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics", type=Path, required=True, help="Owner-opt-in .gz NDJSON diagnostics")
    parser.add_argument("--artifact", type=Path, required=True, help="GitHub workflow ZIP containing APK and manifest")
    args = parser.parse_args()
    try:
        version, installed_signer = evidence_from_diagnostics(args.diagnostics)
        manifest, candidate_signer = evidence_from_artifact(args.artifact)
        result = assess(version, installed_signer, manifest, candidate_signer)
    except (
        ValueError, OSError, EOFError, gzip.BadGzipFile, zipfile.BadZipFile,
        UnicodeDecodeError, json.JSONDecodeError, TypeError, KeyError,
    ) as error:
        print(json.dumps({
            "schema": "sentinel.physical-test-install-preflight.v1",
            "status": "INVALID_EVIDENCE",
            "reason": str(error),
        }, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "ELIGIBLE_FOR_OWNER_DEVICE_CONFIRMATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
