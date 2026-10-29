#!/usr/bin/env python3
from __future__ import annotations

import unittest

from android_release_version_preflight import verify

SOURCE = 'val canonicalVersionCode = 10007\napplicationId = "com.alpha0.app"\n'


class ReleaseVersionPreflightTests(unittest.TestCase):
    def test_approved_first_release(self):
        self.assertEqual(verify(SOURCE, "0", "true"), 10007)

    def test_update_requires_strictly_higher_version(self):
        self.assertEqual(verify(SOURCE, "10006", "false"), 10007)
        for previous in ("10007", "10008", "2100000000"):
            with self.subTest(previous=previous), self.assertRaisesRegex(ValueError, "RELEASE_VERSION_NOT_HIGHER"):
                verify(SOURCE, previous, "false")

    def test_missing_approval_and_lineage_reset_rejected(self):
        with self.assertRaisesRegex(ValueError, "FIRST_RELEASE_LINEAGE_REQUIRES"):
            verify(SOURCE, "0", "false")
        with self.assertRaisesRegex(ValueError, "EXISTING_RELEASE_LINEAGE_CANNOT_BE_RESET"):
            verify(SOURCE, "10006", "true")

    def test_invalid_baseline_does_not_coerce(self):
        for previous in ("", "-1", "01", "1e3", "10006.0", "10000000000"):
            with self.subTest(previous=previous), self.assertRaises(ValueError):
                verify(SOURCE, previous, "false")

    def test_signed_apk_must_match_package_and_exact_version(self):
        self.assertEqual(verify(SOURCE, "10006", "false",
                                "package: name='com.alpha0.app' versionCode='10007' versionName='1.0.0'\n"), 10007)
        for badging in ("", "package: name='com.alpha0.app.physicaltest' versionCode='10007'\n",
                        "package: name='com.alpha0.app' versionCode='10006'\n",
                        "package: name='com.alpha0.app' versionCode='10007'\npackage: name='com.alpha0.app' versionCode='10007'\n"):
            with self.subTest(badging=badging), self.assertRaisesRegex(ValueError, "SIGNED_RELEASE_APK_IDENTITY_MISMATCH"):
                verify(SOURCE, "10006", "false", badging)

    def test_release_app_id_and_version_source_cannot_drift(self):
        for source in (SOURCE.replace("com.alpha0.app", "com.alpha0.app2"),
                       SOURCE.replace("canonicalVersionCode = 10007", "canonicalVersionCode = 0"),
                       SOURCE + "val canonicalVersionCode = 10008\n"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                verify(source, "0", "true")

    def test_approval_must_be_explicit_boolean(self):
        with self.assertRaisesRegex(ValueError, "INVALID_FIRST_RELEASE_APPROVAL"):
            verify(SOURCE, "0", "yes")


if __name__ == "__main__":
    unittest.main()
