#!/usr/bin/env python3
from __future__ import annotations

import unittest

from physical_test_signer_baseline import verify

INSTALLED = "e" * 64
DIFFERENT = "f" * 64


class PhysicalSignerBaselineTests(unittest.TestCase):
    def test_existing_install_requires_exact_same_certificate(self) -> None:
        self.assertEqual(
            verify("100000893", INSTALLED, INSTALLED, "false"),
            "MATCHING_OWNER_SUPPLIED_CERTIFICATES_DEVICE_VERIFICATION_STILL_REQUIRED",
        )

    def test_existing_install_rejects_new_certificate_even_with_higher_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "INSTALLED_SIGNER_MISMATCH"):
            verify("100000893", INSTALLED, DIFFERENT, "false")

    def test_existing_install_rejects_missing_or_malformed_evidence(self) -> None:
        for value in ("none", "", "NOT_VERIFIED", "E" * 64, "1" * 63):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "INSTALLED_CERTIFICATE_EVIDENCE_REQUIRED"):
                verify("100000893", value, INSTALLED, "false")

    def test_first_install_requires_owner_approval_and_no_prior_package(self) -> None:
        with self.assertRaisesRegex(ValueError, "NEW_IDENTITY_REQUIRES"):
            verify("0", "none", INSTALLED, "false")
        with self.assertRaisesRegex(ValueError, "NEW_IDENTITY_REQUIRES"):
            verify("0", DIFFERENT, INSTALLED, "true")
        self.assertEqual(verify("0", "none", INSTALLED, "true"),
                         "NEW_IDENTITY_OWNER_APPROVED_NOT_AN_UPDATE")

    def test_cannot_mix_replacement_approval_with_update(self) -> None:
        with self.assertRaisesRegex(ValueError, "CANNOT_MIX"):
            verify("100000893", INSTALLED, INSTALLED, "true")

    def test_versions_and_signer_pins_fail_closed(self) -> None:
        for value in ("-1", "", "01", "1.0", "2100000001", "10000000000"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "INVALID_PREVIOUS_VERSION_CODE"):
                verify(value, INSTALLED, INSTALLED, "false")
        with self.assertRaisesRegex(ValueError, "INVALID_PINNED_SIGNER"):
            verify("100000893", INSTALLED, "unknown", "false")
        with self.assertRaisesRegex(ValueError, "INVALID_NEW_IDENTITY_APPROVAL"):
            verify("100000893", INSTALLED, INSTALLED, "maybe")


if __name__ == "__main__":
    unittest.main()
