#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from supply_chain_evidence import build_evidence, canonical_digest, verify_evidence

SHA = "a" * 40
REPO = "spenskoj90-sudo/alpha-0"
VERSION = "1.0.0-rc2"


class SupplyChainEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "python.json").write_text(
            json.dumps([{"name": "fastapi", "version": "0.116.1"}, {"name": "sentinel-core", "version": "1.0.0rc2"}]),
            encoding="utf-8",
        )
        (self.root / "package-lock.json").write_text(
            json.dumps({
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "sentinel-dashboard", "version": VERSION},
                    "node_modules/next": {"version": "16.3.4", "integrity": "sha512-test"},
                    "node_modules/vitest": {"version": "4.1.11", "dev": True},
                },
            }),
            encoding="utf-8",
        )
        (self.root / "gradle.txt").write_text(
            "+--- androidx.activity:activity-compose:1.10.0 -> 1.10.1\n\\--- io.sentry:sentry-android:8.54.0\n",
            encoding="utf-8",
        )
        (self.root / "launcher.json").write_text(
            json.dumps({
                "dependencies": {"electron": "37.2.0"},
                "sentinelPackaging": {
                    "electronVersion": "37.2.0",
                    "electronWin32X64Sha256": "4" * 64,
                },
            }),
            encoding="utf-8",
        )
        (self.root / "container.cdx.json").write_text(
            json.dumps({
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "components": [{"type": "library", "name": "openssl", "version": "3.0"}],
            }),
            encoding="utf-8",
        )
        (self.root / "image-id.txt").write_text("sha256:" + "b" * 64 + "\n", encoding="utf-8")
        self.out = self.root / "out"

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return build_evidence(
            repository=REPO,
            sha=SHA,
            version=VERSION,
            python_runtime=self.root / "python.json",
            web_lock=self.root / "package-lock.json",
            gradle_deps=self.root / "gradle.txt",
            launcher_package=self.root / "launcher.json",
            container_sbom=self.root / "container.cdx.json",
            container_image_id=self.root / "image-id.txt",
            output_dir=self.out,
        )

    def test_build_and_verify_exact_source_bound_evidence(self):
        manifest = self.build()
        self.assertEqual(manifest["source"]["sha"], SHA)
        self.assertGreaterEqual(manifest["application"]["sbom"]["componentCount"], 6)
        self.assertEqual(manifest["container"]["sbom"]["componentCount"], 1)
        verified = verify_evidence(self.out, expected_repository=REPO, expected_sha=SHA, expected_version=VERSION)
        self.assertEqual(verified["evidenceDigest"], manifest["evidenceDigest"])

    def test_gradle_resolution_uses_selected_version(self):
        manifest = self.build()
        app = json.loads((self.out / manifest["application"]["sbom"]["path"]).read_text(encoding="utf-8"))
        versions = {(item["name"], item["version"]) for item in app["components"]}
        self.assertIn(("androidx.activity:activity-compose", "1.10.1"), versions)

    def test_sbom_tampering_fails(self):
        manifest = self.build()
        app_path = self.out / manifest["application"]["sbom"]["path"]
        app_path.write_text(app_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            verify_evidence(self.out)

    def test_source_sha_tampering_fails_even_with_recomputed_manifest_digest(self):
        self.build()
        manifest_path = self.out / "supply-chain-evidence.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source"]["sha"] = "c" * 40
        manifest["evidenceDigest"] = canonical_digest(manifest)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source binding mismatch"):
            verify_evidence(self.out)

    def test_release_or_attestation_overclaim_fails(self):
        self.build()
        manifest_path = self.out / "supply-chain-evidence.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["claims"]["cryptographicAttestationProduced"] = True
        manifest["evidenceDigest"] = canonical_digest(manifest)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must not overclaim"):
            verify_evidence(self.out)

    def test_invalid_launcher_runtime_hash_fails(self):
        launcher = json.loads((self.root / "launcher.json").read_text(encoding="utf-8"))
        launcher["sentinelPackaging"]["electronWin32X64Sha256"] = "not-a-hash"
        (self.root / "launcher.json").write_text(json.dumps(launcher), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "runtime SHA-256"):
            self.build()


if __name__ == "__main__":
    unittest.main()
