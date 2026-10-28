#!/usr/bin/env python3
"""Credential-free negative tests for the inert B2 endpoint contract."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

from b2_target_contract import require_version_id, validate_target

ENDPOINT = "https://s3.eu-central-003.backblazeb2.com"
REGION = "eu-central-003"
BUCKET = "sentinel-b2-private-test"


class StaticB2ContractTests(unittest.TestCase):
    def assert_denied(self, endpoint=ENDPOINT, region=REGION, bucket=BUCKET, size=100_000_000):
        with self.assertRaises(ValueError):
            validate_target(endpoint, region, bucket, size)

    def test_explicit_eu_target_is_syntactically_valid(self):
        validate_target(ENDPOINT, REGION, BUCKET, 100_000_000)

    def test_no_region_guessing(self):
        self.assert_denied(region="")

    def test_non_eu_region_denied(self):
        self.assert_denied(endpoint="https://s3.us-west-004.backblazeb2.com", region="us-west-004")

    def test_region_endpoint_mismatch_denied(self):
        self.assert_denied(region="eu-central-004")

    def test_insecure_scheme_denied(self):
        self.assert_denied(endpoint="http://s3.eu-central-003.backblazeb2.com")

    def test_suffix_attack_denied(self):
        self.assert_denied(endpoint=ENDPOINT + ".evil.invalid")

    def test_credentials_in_url_denied(self):
        self.assert_denied(endpoint="https://user:pass@s3.eu-central-003.backblazeb2.com")

    def test_path_and_query_denied(self):
        self.assert_denied(endpoint=ENDPOINT + "/bucket?x=1")

    def test_nonstandard_port_denied(self):
        self.assert_denied(endpoint=ENDPOINT + ":443")

    def test_bucket_dot_denied_to_avoid_tls_wildcard_issues(self):
        self.assert_denied(bucket="sentinel.backup")

    def test_bucket_invalid_characters_denied(self):
        self.assert_denied(bucket="Sentinel_secret")

    def test_missing_byte_cap_denied(self):
        self.assert_denied(size=0)

    def test_bool_byte_cap_denied(self):
        self.assert_denied(size=True)

    def test_nonexistent_version_denied(self):
        for value in ("", "None", "null", "-", "foo\nbar"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_version_id(value)

    def test_opaque_valid_version_not_reinterpreted(self):
        require_version_id("4_zabc0123_version-123")

    def test_cli_labels_success_as_static_only(self):
        script = pathlib.Path(__file__).with_name("b2_target_contract.py")
        p = subprocess.run([sys.executable, str(script), "--endpoint", ENDPOINT, "--region", REGION,
                            "--bucket", BUCKET, "--max-ciphertext-bytes", "100000000"],
                           capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("STATIC_B2_CONTRACT_PASS", p.stdout)
        self.assertIn("NOT_VERIFIED", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
