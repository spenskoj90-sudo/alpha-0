"""Synthetic CLI/metadata fixtures + real OpenSSL signatures, NOT a real APK acceptance test."""
import base64
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from signed_update_feed_release import APPROVED_SIGNER, make


class OfflineFeedProducerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        self.apk = self.p / "fake.apk"
        self.apk.write_bytes(b"synthetic-APK-not-an-installable-package")
        self.notes = self.p / "notes.txt"
        self.notes.write_text("Changed calibration UI\n", encoding="utf-8")
        self.signer = APPROVED_SIGNER
        self.aapt2 = self.p / "aapt2"
        self.apksigner = self.p / "apksigner"
        self.aapt2.write_text("#!/bin/sh\nprintf \"package: name='com.alpha0.app' versionCode='10008' versionName='v2'\\n\"\n")
        self.apksigner.write_text("#!/bin/sh\nprintf 'Signer #1 certificate SHA-256 digest: " + self.signer + "\\n'\n")
        self.aapt2.chmod(0o700)
        self.apksigner.chmod(0o700)
        self.private = self.p / "feed-key.pem"
        subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(self.private)], check=True, stdout=subprocess.DEVNULL)
        self.public = self.p / "feed-public.pem"
        subprocess.run(["openssl", "pkey", "-in", str(self.private), "-pubout", "-out", str(self.public)], check=True, stdout=subprocess.DEVNULL)
        der = subprocess.check_output(["openssl", "pkey", "-in", str(self.private), "-pubout", "-outform", "DER"])
        self.args = SimpleNamespace(apk=self.apk, notes=self.notes, aapt2=str(self.aapt2),
            apksigner=str(self.apksigner), feed_url="https://updates.example.org/android/feed.txt",
            apk_url="https://updates.example.org/android/sentinel-v2.apk", expected_signer=self.signer,
            previous_version=10007, feed_private_key=self.private,
            verifying_key=base64.b64encode(der).decode("ascii"), output=self.p / "feed.txt")

    def test_wire_matches_android_contract_and_real_signature(self):
        sha = make(self.args)
        wire = self.args.output.read_bytes()
        lines = wire.split(b"\n")
        self.assertEqual(4, len(lines))
        self.assertEqual(b"SENTINEL-SIGNED-FEED-v1", lines[0])
        self.assertEqual(b"", lines[-1])
        decode = lambda x: base64.urlsafe_b64decode(x + b"=" * (-len(x) % 4))
        manifest, signature = decode(lines[1]), decode(lines[2])
        self.assertIn(b"package=com.alpha0.app\nversionCode=10008\n", manifest)
        self.assertIn(b"certificateSha256=" + self.signer.encode("ascii"), manifest)
        self.assertIn(b"apkSha256=" + sha.encode("ascii"), manifest)
        self.assertEqual(hashlib.sha256(self.apk.read_bytes()).hexdigest(), sha)
        sigfile = self.p / "sig.der"
        sigfile.write_bytes(signature)
        good = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(self.public),
                              "-signature", str(sigfile)], input=manifest, capture_output=True)
        self.assertEqual(0, good.returncode, good.stderr)
        bad = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(self.public),
                             "-signature", str(sigfile)], input=manifest.replace(b"10008", b"10009"), capture_output=True)
        self.assertNotEqual(0, bad.returncode)
        with self.assertRaises(FileExistsError):
            make(self.args)

    def test_identity_and_signer_fail_closed(self):
        self.args.previous_version = 10008
        with self.assertRaisesRegex(ValueError, "strictly exceed"):
            make(self.args)
        self.args.previous_version = 10007
        self.args.expected_signer = "b" * 64
        with self.assertRaisesRegex(ValueError, "invalid release signer"):
            make(self.args)
        self.args.expected_signer = self.signer
        self.aapt2.write_text("#!/bin/sh\nprintf \"package: name='com.other.app' versionCode='10008'\\n\"\n")
        with self.assertRaisesRegex(ValueError, "application ID"):
            make(self.args)
        self.assertFalse(self.args.output.exists())

    def test_bad_urls_keys_and_notes_never_produce_feed(self):
        self.args.apk_url = "https://evil.example.org/file.apk"
        with self.assertRaisesRegex(ValueError, "exact HTTPS origin"):
            make(self.args)
        self.args.apk_url = "https://updates.example.org/android/%2e%2e/file.apk"
        with self.assertRaisesRegex(ValueError, "strict HTTPS"):
            make(self.args)
        self.args.apk_url = "https://updates.example.org/android/sentinel-v2.apk"
        self.args.verifying_key = base64.b64encode(b"wrong public key").decode("ascii")
        with self.assertRaisesRegex(ValueError, "approved public pin"):
            make(self.args)
        derived = subprocess.check_output(["openssl", "pkey", "-in", str(self.private), "-pubout", "-outform", "DER"])
        self.args.verifying_key = base64.b64encode(derived).decode("ascii")
        self.notes.write_text("\u202eSpoof release\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid release notes"):
            make(self.args)
        self.assertFalse(self.args.output.exists())


if __name__ == "__main__":
    unittest.main()
