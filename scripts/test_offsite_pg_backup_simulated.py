#!/usr/bin/env python3
"""A local fake transport for the R2 backup pipeline: NO actual encryption or cloud call.

Real off-provider backup and independent decryption/pg_restore are still required.
These tests use only fake fixtures, fake credentials, fake docker/age/aws commands.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/offsite_pg_backup.sh"

DOCKER = """#!/usr/bin/env python3
import os, sys
if os.environ.get("MOCK_DUMP_FAILURE") == "1":
    sys.exit(42)
sys.stdout.buffer.write(b"SAFE_SYNTHETIC_DATABASE_FIXTURE_" * 160)
"""

AGE = """#!/usr/bin/env python3
import pathlib, sys
args = sys.argv
output = args[args.index("--output") + 1]
payload = sys.stdin.buffer.read()
# This is a fake cipher output solely to test the command pipeline, NOT crypto.
pathlib.Path(output).write_bytes(b"FAKE_CIPHERTEXT_FOR_TEST_ONLY:" + payload[::-1])
"""

AWS = """#!/usr/bin/env python3
import os, pathlib, shutil, sys
args = sys.argv
j = args.index("cp")
src, dest = args[-2:]
remote = pathlib.Path(os.environ["MOCK_REMOTE_OBJECT"])
if src.startswith("s3://"):
    shutil.copyfile(remote, dest)
    if os.environ.get("MOCK_CORRUPT_DOWNLOAD") == "1":
        with open(dest, "ab") as f:
            f.write(b"MISMATCH")
else:
    remote.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, remote)
"""


class SimulatedR2Pipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="test-sentinel-r2-")
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        bindir = self.base / "bin"
        bindir.mkdir()
        for name, source in [("docker", DOCKER), ("age", AGE), ("aws", AWS)]:
            path = bindir / name
            path.write_text(textwrap.dedent(source))
            path.chmod(0o700)
        self.remote = self.base / "offsite" / "object.age"
        self.summary = self.base / "summary.txt"
        self.env = {
            "PATH": str(bindir) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"),
            "GITHUB_REPOSITORY": "spenskoj90-sudo/alpha-0",
            "GITHUB_REF": "refs/heads/main",
            "DATABASE_URL": "postgresql://backup:TEST_PASS@db.neon.tech/sentinel?sslmode=require",
            "BACKUP_EXPECTED_HOST": "db.neon.tech",
            "BACKUP_EXPECTED_DATABASE": "sentinel",
            "BACKUP_AGE_RECIPIENT": "age1" + "q" * 58,
            "BACKUP_S3_BUCKET": "private-test-backups",
            "BACKUP_R2_ENDPOINT": "https://" + "a" * 32 + ".r2.cloudflarestorage.com",
            "AWS_ACCESS_KEY_ID": "TEST_R2_ID",
            "AWS_SECRET_ACCESS_KEY": "TEST_R2_SECRET",
            "AWS_REGION": "auto",
            "RUNNER_TEMP": str(self.base),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "MOCK_REMOTE_OBJECT": str(self.remote),
        }

    def run_export(self, **changes: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", str(SCRIPT)],
                              env={**self.env, **changes},
                              capture_output=True, text=True, timeout=15, check=False)

    def test_fake_upload_roundtrip_and_no_secrets_in_summary(self) -> None:
        result = self.run_export()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.remote.is_file())
        self.assertTrue(self.remote.read_bytes().startswith(b"FAKE_CIPHERTEXT_FOR_TEST_ONLY:"))
        self.assertFalse(self.remote.read_bytes().startswith(b"SAFE_SYNTHETIC_DATABASE"))
        summary = self.summary.read_text()
        self.assertIn("Cloudflare R2 object:", summary)
        self.assertIn("Restore status: NOT VERIFIED", summary)
        for secret in ("TEST_PASS", "TEST_R2_SECRET"):
            self.assertNotIn(secret, summary + result.stdout + result.stderr)

    def test_remote_mismatch_rejected(self) -> None:
        result = self.run_export(MOCK_CORRUPT_DOWNLOAD="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("remote ciphertext mismatch", result.stderr)
        self.assertTrue(self.remote.is_file())
        self.assertFalse(self.summary.exists())

    def test_failed_dump_cannot_upload_anything(self) -> None:
        result = self.run_export(MOCK_DUMP_FAILURE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.remote.exists())
        self.assertFalse(self.summary.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
