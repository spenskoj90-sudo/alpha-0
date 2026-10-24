#!/usr/bin/env python3
"""Local, credential-free contract tests for the *inactive* backup workflow."""
from __future__ import annotations
import os
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/offsite_pg_backup.sh"
WORKFLOW = ROOT / ".github/workflows/offsite-db-backup.yml"


def check(extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "GITHUB_REPOSITORY": "spenskoj90-sudo/alpha-0",
           "GITHUB_REF": "refs/heads/main"}
    env.update(extra)
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True,
                          text=True, timeout=10, check=False)


class BackupContractTests(unittest.TestCase):
    def test_bash_syntax(self) -> None:
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_invalid_repository_denied(self) -> None:
        result = check({"GITHUB_REPOSITORY": "other/repo"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected repository", result.stderr)

    def test_non_main_denied(self) -> None:
        result = check({"GITHUB_REF": "refs/heads/topic"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protected main", result.stderr)

    def test_missing_secret_denied(self) -> None:
        result = check({})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing unpooled", result.stderr)

    def test_source_mismatch_denied_without_leaking_url(self) -> None:
        url = "postgresql://readonly:TEST_PASSWORD@wrong.neon.tech/sentinel?sslmode=require"
        result = check({
            "DATABASE_URL": url,
            "BACKUP_EXPECTED_HOST": "expected.neon.tech",
            "BACKUP_EXPECTED_DATABASE": "sentinel",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source connection identity/TLS", result.stderr)
        self.assertNotIn("TEST_PASSWORD", result.stderr)

    def test_missing_tls_denied(self) -> None:
        result = check({
            "DATABASE_URL": "postgresql://readonly:TEST_PASSWORD@expected.neon.tech/sentinel",
            "BACKUP_EXPECTED_HOST": "expected.neon.tech",
            "BACKUP_EXPECTED_DATABASE": "sentinel",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source connection identity/TLS", result.stderr)

    def test_wrong_database_denied(self) -> None:
        result = check({
            "DATABASE_URL": "postgresql://readonly:TEST_PASSWORD@expected.neon.tech/other?sslmode=require",
            "BACKUP_EXPECTED_HOST": "expected.neon.tech",
            "BACKUP_EXPECTED_DATABASE": "sentinel",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source connection identity/TLS", result.stderr)

    def test_workflow_is_manual_only_and_oidc_bounded(self) -> None:
        s = WORKFLOW.read_text()
        self.assertIn("  workflow_dispatch:", s)
        self.assertNotIn("  schedule:", s)
        self.assertNotIn("  pull_request:", s)
        self.assertIn("refs/heads/main", s)
        self.assertNotIn("id-token: write", s)
        self.assertIn("secrets.SENTINEL_BACKUP_R2_SECRET_ACCESS_KEY", s)
        self.assertIn("secrets.SENTINEL_BACKUP_R2_ACCESS_KEY_ID", s)
        self.assertIn("persist-credentials: false", s)
        self.assertIn("secrets.SENTINEL_BACKUP_DATABASE_URL", s)
        self.assertIn("BACKUP_EXPECTED_HOST:", s)
        self.assertIn("BACKUP_EXPECTED_DATABASE:", s)


    def test_invalid_r2_endpoint_denied(self) -> None:
        result = check({
            "DATABASE_URL": "postgresql://backup:FAKE_PASSWORD@expected.neon.tech/sentinel?sslmode=require",
            "BACKUP_EXPECTED_HOST": "expected.neon.tech",
            "BACKUP_EXPECTED_DATABASE": "sentinel",
            "BACKUP_AGE_RECIPIENT": "age1" + "q" * 58,
            "BACKUP_S3_BUCKET": "sentinel-backups",
            "BACKUP_R2_ENDPOINT": "https://malicious.invalid",
            "AWS_ACCESS_KEY_ID": "FAKE",
            "AWS_SECRET_ACCESS_KEY": "FAKE",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid Cloudflare R2 endpoint", result.stderr)
        self.assertNotIn("FAKE_PASSWORD", result.stderr)

    def test_missing_r2_credentials_denied(self) -> None:
        result = check({
            "DATABASE_URL": "postgresql://backup:FAKE_PASSWORD@expected.neon.tech/sentinel?sslmode=require",
            "BACKUP_EXPECTED_HOST": "expected.neon.tech",
            "BACKUP_EXPECTED_DATABASE": "sentinel",
            "BACKUP_AGE_RECIPIENT": "age1" + "q" * 58,
            "BACKUP_S3_BUCKET": "sentinel-backups",
            "BACKUP_R2_ENDPOINT": "https://" + "a" * 32 + ".r2.cloudflarestorage.com",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("R2 limited-scope", result.stderr)
        self.assertNotIn("FAKE_PASSWORD", result.stderr)

    def test_backup_is_encrypted_before_offsite_storage(self) -> None:
        s = SCRIPT.read_text()
        self.assertIn("set -euo pipefail", s)
        self.assertIn("| age --encrypt", s)
        self.assertIn("aws --endpoint-url", s)
        self.assertNotIn("--sse AES256 \"$ciphertext\"", s)
        self.assertIn("r2.cloudflarestorage", s)
        self.assertIn('cmp -s "$ciphertext" "$download"', s)
        self.assertNotIn("\\npg_restore ", s)  # Mentioning restore in the summary is allowed
        self.assertNotIn("set -x", s)
        self.assertNotIn("--no-password", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
