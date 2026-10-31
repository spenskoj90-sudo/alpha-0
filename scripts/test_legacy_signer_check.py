#!/usr/bin/env python3
"""Real ephemeral keytool fixtures; never use a product signing key."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/legacy_signer_check.py"
SHA = "a" * 40
WORKFLOW = "spenskoj90-sudo/alpha-0/.github/workflows/legacy-signer-check.yml@refs/heads/main"


class LegacySignerCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="synthetic-signer-test-", dir="/dev/shm")
        cls.directory = Path(cls.tmp.name)
        cls.password = "synthetic-only-" + os.urandom(16).hex()
        cls.alias = "synthetic-check-only"
        password_file = cls.directory / "password"
        password_file.write_text(cls.password)
        password_file.chmod(0o600)
        cls.fixtures = {}
        for kind in ("PKCS12", "JKS"):
            key = cls.directory / kind
            cert = cls.directory / (kind + ".der")
            subprocess.run([
                "keytool", "-genkeypair", "-noprompt", "-storetype", kind,
                "-keystore", str(key), "-storepass:file", str(password_file),
                "-keypass:file", str(password_file), "-alias", cls.alias,
                "-keyalg", "RSA", "-keysize", "2048", "-validity", "1",
                "-dname", "CN=Synthetic Test Only",
            ], check=True, capture_output=True)
            subprocess.run([
                "keytool", "-exportcert", "-keystore", str(key),
                "-storepass:file", str(password_file), "-alias", cls.alias,
                "-file", str(cert),
            ], check=True, capture_output=True)
            cls.fixtures[kind] = (key.read_bytes(), hashlib.sha256(cert.read_bytes()).hexdigest())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self, kind="PKCS12", *, overrides=None, expected=None):
        blob, pin = self.fixtures[kind]
        env = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8",
               "GITHUB_REPOSITORY": "spenskoj90-sudo/alpha-0",
               "GITHUB_REPOSITORY_ID": "1328718401", "GITHUB_REF": "refs/heads/main",
               "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_SHA": SHA,
               "GITHUB_WORKFLOW_REF": WORKFLOW,
               "LEGACY_KEYSTORE_BASE64": base64.b64encode(blob).decode(),
               "LEGACY_KEYSTORE_PASSWORD": self.password,
               "LEGACY_KEY_ALIAS": self.alias, "LEGACY_KEY_PASSWORD": self.password}
        env.update(overrides or {})
        before = set(Path("/dev/shm").glob("sentinel-key-check-*"))
        result = subprocess.run([
            "python", str(SCRIPT), "--source-sha", SHA,
            "--expected-certificate-sha256", expected or pin,
        ], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(before, set(Path("/dev/shm").glob("sentinel-key-check-*")), "temporary key material leaked")
        self.assertNotIn(self.password, result.stdout + result.stderr)
        self.assertNotIn(env["LEGACY_KEYSTORE_BASE64"], result.stdout + result.stderr)
        return result

    def test_pkcs12_proves_key_use_without_exporting_key_or_signing_apk(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["certificateSha256"], self.fixtures["PKCS12"][1])
        self.assertEqual(evidence["privateKeyProof"], "PASS")
        self.assertFalse(evidence["apkSigned"])
        self.assertFalse(evidence["keyExported"])
        self.assertEqual(evidence["custodyRestore"], "NOT_RUN")

    def test_legacy_jks_is_supported_without_conversion_or_mutation(self):
        result = self.run_check("JKS")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["keystoreSha256"], hashlib.sha256(self.fixtures["JKS"][0]).hexdigest())

    def test_certificate_mismatch_fails_closed_and_reports_only_public_identity(self):
        result = self.run_check(expected="0" * 64)
        self.assertEqual(result.returncode, 1)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["stage"], "certificate-pin")
        self.assertEqual(evidence["certificateSha256"], self.fixtures["PKCS12"][1])

    def test_wrong_key_password_fails_without_echoing_tool_diagnostics(self):
        result = self.run_check("JKS", overrides={"LEGACY_KEY_PASSWORD": "wrong-sensitive-key-password"})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["stage"], "private-key-proof")
        self.assertNotIn("wrong-sensitive-key-password", result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")

    def test_untrusted_contexts_are_denied_before_key_decode(self):
        for changes in ({"GITHUB_REF": "refs/heads/feature"},
                        {"GITHUB_EVENT_NAME": "pull_request"},
                        {"GITHUB_REPOSITORY_ID": "1416856833"},
                        {"GITHUB_SHA": "b" * 40},
                        {"GITHUB_WORKFLOW_REF": WORKFLOW.replace("legacy-signer-check", "other")}):
            with self.subTest(changes=changes):
                result = self.run_check(overrides={**changes, "LEGACY_KEYSTORE_BASE64": "invalid-secret-data"})
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["stage"], "run-context")

    def test_malformed_key_fails_without_printing_values(self):
        result = self.run_check(overrides={"LEGACY_KEYSTORE_BASE64": "invalid-secret-data"})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["stage"], "input")


if __name__ == "__main__":
    unittest.main()
