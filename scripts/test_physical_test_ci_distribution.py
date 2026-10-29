#!/usr/bin/env python3
"""Regression: routine public CI must never hand Owners an ephemeral installable APK."""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ROUTINE_WORKFLOW = ROOT / ".github" / "workflows" / "physical-test-apk.yml"
STABLE_WORKFLOW = ROOT / ".github" / "workflows" / "physical-test-update-apk.yml"


class PhysicalTestCiDistributionTests(unittest.TestCase):
    def test_routine_artifact_contains_no_installable_apk(self) -> None:
        text = ROUTINE_WORKFLOW.read_text(encoding="utf-8")
        start = text.index("      - name: Upload exact-SHA CI-only metadata (exclude APK bytes)")
        upload = text[start:]
        self.assertIn("name: sentinel-ci-only-physical-test-evidence-", upload)
        self.assertIn("physical-test-manifest.json", upload)
        self.assertIn("PHYSICAL_TEST_CI_ONLY.txt", upload)
        self.assertNotIn("app-physicalTest.apk", upload)
        self.assertNotIn("app/build/outputs/apk/physicalTest/", upload)

    def test_ephemeral_build_fails_closed_before_metadata_publication(self) -> None:
        text = ROUTINE_WORKFLOW.read_text(encoding="utf-8")
        guard = text.index("      - name: Enforce CI-only diagnostic artifact")
        upload = text.index("      - name: Upload exact-SHA CI-only metadata")
        self.assertLess(guard, upload)
        self.assertIn('assert manifest["signingMode"] == "ephemeral-debug"', text[guard:upload])
        self.assertIn('assert manifest["updateCompatible"] is False', text[guard:upload])
        self.assertIn('assert manifest["signerLineageVerified"] is False', text[guard:upload])
        self.assertIn("DO NOT INSTALL ON A PHONE", text[guard:upload])

    def test_stable_owner_workflow_remains_separate_and_signer_pinned(self) -> None:
        text = STABLE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: Physical Test Update APK", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("PHYSICAL_TEST_EXPECTED_SIGNER_SHA256", text)
        self.assertIn("PHYSICAL_TEST_KEYSTORE_BASE64", text)
        self.assertIn("signing-mode stable-test", text)
        self.assertIn("updateCompatible", text)
        self.assertIn("installed_signer_sha256:", text)
        self.assertIn("new_identity_approved:", text)
        self.assertIn("Enforce installed-certificate match before any signing-key access", text)
        self.assertIn("scripts/physical_test_signer_baseline.py", text)


if __name__ == "__main__":
    unittest.main()
