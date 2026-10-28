#!/usr/bin/env python3
"""Offline preflight guard tests; all fixture signers are synthetic."""
from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from physical_test_install_preflight import (
    assess, evidence_from_artifact, evidence_from_diagnostics,
)

APP_ID = "com.alpha0.app.physicaltest"
OLD = "a" * 64
NEW = "b" * 64


class PhysicalInstallPreflightTests(unittest.TestCase):
    def diagnostic(self, path: Path, *, signer: str = OLD, version: int = 718, corrupt: bool = False):
        rows = [
            {"event": "PROCESS_START", "details": {
                "package_name": APP_ID, "build_type": "physicalTest", "version_code": version,
            }},
            {"event": "PACKAGE_SIGNER", "details": {
                "package_name": APP_ID, "installed_version_code": version,
                "signer_count": 1, "multiple_signers": False, "signer_cert_sha256": signer,
            }},
        ]
        if corrupt:
            rows.append(rows[0])
        with gzip.open(path, "wt") as dest:
            for row in rows:
                dest.write(json.dumps(row) + "\n")

    def artifact(self, path: Path, *, signer: str = NEW, version: int = 752,
                 stable: bool = False, baseline: int = 718, tamper: bool = False):
        apk = b"fake offline fixture for digest verification"
        manifest = {
            "schema": "sentinel.android-physical-test-artifact.v1",
            "sourceSha": "c" * 40,
            "signerCertificateSha256": signer,
            "signingMode": "stable-test" if stable else "ephemeral-debug",
            "signerLineageVerified": stable,
            "updateCompatible": stable,
            "updateBaselineVersionCode": baseline if stable else None,
            "apiEnvironment": "staging",
            "runtimeEnvironment": "staging",
            "apiBaseUrl": "https://sentinel-core-staging.onrender.com",
            "apiFallbackBaseUrl": "https://sentinel-web-staging-fxhn.onrender.com/api/mobile-core",
            "apk": {
                "applicationId": APP_ID, "buildVariant": "physicalTest",
                "versionCode": version, "sizeBytes": len(apk),
                "sha256": hashlib.sha256(apk).hexdigest(),
            },
        }
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("physical-test-manifest.json", json.dumps(manifest))
            archive.writestr("app/build/outputs/apk/physicalTest/app-physicalTest.apk",
                             apk + (b"tamper" if tamper else b""))
        return manifest

    def test_owner_situation_blocks_mismatched_cert_despite_higher_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.diagnostic(root / "diag.gz")
            self.artifact(root / "artifact.zip")
            installed, signer = evidence_from_diagnostics(root / "diag.gz")
            manifest, candidate = evidence_from_artifact(root / "artifact.zip")
            result = assess(installed, signer, manifest, candidate)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["reason"], "SIGNER_MISMATCH")

    def test_matched_stable_lineage_only_qualifies_for_device_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.diagnostic(root / "diag.gz")
            self.artifact(root / "artifact.zip", signer=OLD, stable=True)
            installed, signer = evidence_from_diagnostics(root / "diag.gz")
            manifest, candidate = evidence_from_artifact(root / "artifact.zip")
            result = assess(installed, signer, manifest, candidate)
            self.assertEqual(result["status"], "ELIGIBLE_FOR_OWNER_DEVICE_CONFIRMATION")
            self.assertFalse(result["apkSignerIndependentlyVerified"])
            self.assertTrue(result["noDeviceOrSigningOperationPerformed"])

    def test_ephemeral_equal_cert_is_not_a_proven_update_lineage(self):
        base = {"apk": {"versionCode": 719}, "sourceSha": "c" * 40,
                "apiEnvironment": "staging", "signingMode": "ephemeral-debug",
                "signerLineageVerified": False, "updateCompatible": False}
        self.assertEqual(assess(718, OLD, base, OLD)["reason"], "UPDATE_LINEAGE_NOT_VERIFIED")

    def test_downgrade_and_unconfirmed_baseline_block(self):
        base = {"apk": {"versionCode": 718}, "sourceSha": "c" * 40,
                "apiEnvironment": "staging", "signingMode": "stable-test",
                "signerLineageVerified": True, "updateCompatible": True,
                "updateBaselineVersionCode": 718}
        self.assertEqual(assess(718, OLD, base, OLD)["reason"], "VERSION_NOT_HIGHER")
        base["apk"]["versionCode"] = 719
        base["updateBaselineVersionCode"] = 717
        self.assertEqual(assess(718, OLD, base, OLD)["reason"], "UPDATE_BASELINE_NOT_PROVEN")

    def test_conflicting_diagnostic_process_identities_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diag.gz"
            self.diagnostic(path, corrupt=True)
            with self.assertRaisesRegex(ValueError, "AMBIGUOUS_INSTALLED_IDENTITY"):
                evidence_from_diagnostics(path)

    def test_apk_tampering_and_duplicate_manifest_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.zip"
            self.artifact(path, tamper=True)
            with self.assertRaisesRegex(ValueError, "APK_SIZE_MISMATCH"):
                evidence_from_artifact(path)
            self.artifact(path)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(path, "a") as archive:
                    archive.writestr("physical-test-manifest.json", "{}")
            with self.assertRaisesRegex(ValueError, "DUPLICATE_ARTIFACT_ENTRIES"):
                evidence_from_artifact(path)


    def test_unexpected_artifact_entries_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.zip"
            self.artifact(path)
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("unexpected-alt.apk", b"untrusted alternate package")
            with self.assertRaisesRegex(ValueError, "UNEXPECTED_ARTIFACT_ENTRIES"):
                evidence_from_artifact(path)

    def test_known_optional_integrity_sidecars_are_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.zip"
            manifest = self.artifact(path)
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("physical-test-apk.sha256", "synthetic digest sidecar")
                archive.writestr("physical-test-signer.txt", "synthetic certificate report")
            actual_manifest, signer = evidence_from_artifact(path)
            self.assertEqual(actual_manifest["sourceSha"], manifest["sourceSha"])
            self.assertEqual(signer, NEW)


if __name__ == "__main__":
    unittest.main()
