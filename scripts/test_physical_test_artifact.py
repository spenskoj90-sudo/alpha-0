#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from physical_test_artifact import build_manifest


SHA = "a" * 40
SIGNER = "b" * 64
SIGNER_SHA1 = "d" * 40
OTHER_SIGNER = "c" * 64
ORIGIN = "https://sentinel-core-staging.onrender.com"
FALLBACK = "https://sentinel-web-staging-fxhn.onrender.com/api/mobile-core"
CALLBACK = "com.alpha0.app.physicaltest.auth"
VK_ID = "123456"
VK_REDIRECT = f"vk{VK_ID}://vk.ru/blank.html"


class PhysicalTestArtifactTests(unittest.TestCase):
    def fixture(self, root: Path, *, dex_suffix: bytes = b"", application_id: str = "com.alpha0.app.physicaltest") -> tuple[Path, Path, Path]:
        apk = root / "app-physicalTest.apk"
        with zipfile.ZipFile(apk, "w") as archive:
            archive.writestr(
                "classes.dex",
                b"dex\n"
                + SHA.encode()
                + b"\n"
                + ORIGIN.encode()
                + b"\n"
                + FALLBACK.encode()
                + b"\nFORENSIC_TEST\n"
                + CALLBACK.encode()
                + b"\n"
                + VK_REDIRECT.encode()
                + b"\n"
                + dex_suffix,
            )
        metadata = root / "output-metadata.json"
        metadata.write_text(
            json.dumps(
                {
                    "artifactType": {"type": "APK"},
                    "applicationId": application_id,
                    "variantName": "physicalTest",
                    "elements": [
                        {
                            "outputFile": apk.name,
                            "versionCode": 10002,
                            "versionName": "1.0.0-rc2-physical-test",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        version = root / "VERSION"
        version.write_text("1.0.0-rc2\n", encoding="utf-8")
        return apk, metadata, version

    def create_manifest(self, root: Path, **fixture_overrides: object) -> dict[str, object]:
        apk, metadata, version = self.fixture(root, **fixture_overrides)
        return build_manifest(
            apk=apk,
            output_metadata=metadata,
            version_file=version,
            source_sha=SHA,
            api_base_url=ORIGIN,
            api_fallback_base_url=FALLBACK,
            repository="spenskoj90-sudo/alpha-0",
            run_id="12345",
            run_attempt="2",
            signer_sha256=SIGNER,
            vk_client_id=VK_ID,
            generated_at="2026-09-16T20:00:00Z",
        )

    def test_manifest_binds_exact_apk_source_staging_and_gradle_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.create_manifest(Path(temp))
        self.assertEqual(manifest["sourceSha"], SHA)
        self.assertEqual(manifest["apiBaseUrl"], ORIGIN)
        self.assertEqual(manifest["apiFallbackBaseUrl"], FALLBACK)
        self.assertEqual(manifest["runtimeEnvironment"], "staging")
        self.assertEqual(manifest["federatedAuth"]["authCallbackScheme"], CALLBACK)
        self.assertEqual(manifest["federatedAuth"]["vkClientId"], VK_ID)
        self.assertEqual(manifest["federatedAuth"]["vkRedirectUri"], VK_REDIRECT)
        self.assertEqual(manifest["signingMode"], "ephemeral-debug")
        self.assertEqual(manifest["signerCertificateSha256"], SIGNER)
        self.assertNotIn("signerCertificateSha1", manifest)
        self.assertFalse(manifest["signerLineageVerified"])
        self.assertFalse(manifest["updateCompatible"])
        self.assertEqual(manifest["workflow"]["name"], "Physical Test APK")
        self.assertEqual(manifest["httpReadTimeoutMs"], 75_000)
        self.assertTrue(manifest["coldStartAware"])
        self.assertEqual(manifest["apk"]["applicationId"], "com.alpha0.app.physicaltest")
        self.assertEqual(len(manifest["apk"]["sha256"]), 64)

    def test_stable_update_manifest_is_explicitly_update_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk, metadata, version = self.fixture(Path(temp))
            manifest = build_manifest(
                apk=apk,
                output_metadata=metadata,
                version_file=version,
                source_sha=SHA,
                api_base_url=ORIGIN,
                api_fallback_base_url=FALLBACK,
                repository="spenskoj90-sudo/alpha-0",
                run_id="12345",
                run_attempt="2",
                signer_sha256=SIGNER,
                signer_sha1=SIGNER_SHA1,
                vk_client_id=VK_ID,
                expected_signer_sha256=SIGNER,
                previous_version_code=10001,
                signing_mode="stable-test",
                workflow_name="Physical Test Update APK",
                generated_at="2026-09-21T15:00:00Z",
            )
        self.assertTrue(manifest["updateCompatible"])
        self.assertTrue(manifest["signerLineageVerified"])
        self.assertEqual(manifest["updateBaselineVersionCode"], 10001)
        self.assertEqual(manifest["signerCertificateSha256"], SIGNER)
        self.assertEqual(manifest["signerCertificateSha1"], SIGNER_SHA1)
        self.assertEqual(manifest["apk"]["applicationId"], "com.alpha0.app.physicaltest")
        self.assertEqual(manifest["signingMode"], "stable-test")
        self.assertEqual(manifest["workflow"]["name"], "Physical Test Update APK")
        self.assertEqual(manifest["artifactName"], f"sentinel-physical-test-update-apk-{SHA}")

    def test_stable_google_oauth_binding_requires_exact_certificate_sha1(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk, metadata, version = self.fixture(Path(temp))
            for signer_sha1 in (None, "", "invalid", "a" * 39, "A" * 41, "g" * 40):
                with self.subTest(signer_sha1=signer_sha1), self.assertRaisesRegex(ValueError, "requires a 40-character signer certificate SHA-1"):
                    build_manifest(
                        apk=apk, output_metadata=metadata, version_file=version,
                        source_sha=SHA, api_base_url=ORIGIN, api_fallback_base_url=FALLBACK,
                        repository="spenskoj90-sudo/alpha-0", run_id="12345", run_attempt="2",
                        signer_sha256=SIGNER, signer_sha1=signer_sha1,
                        expected_signer_sha256=SIGNER, vk_client_id=VK_ID,
                        previous_version_code=10001, signing_mode="stable-test",
                        workflow_name="Physical Test Update APK",
                    )

    def test_ephemeral_signing_cannot_claim_google_oauth_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk, metadata, version = self.fixture(Path(temp))
            with self.assertRaisesRegex(ValueError, "ephemeral-debug artifacts cannot declare"):
                build_manifest(
                    apk=apk, output_metadata=metadata, version_file=version,
                    source_sha=SHA, api_base_url=ORIGIN, api_fallback_base_url=FALLBACK,
                    repository="spenskoj90-sudo/alpha-0", run_id="12345", run_attempt="2",
                    signer_sha256=SIGNER, signer_sha1=SIGNER_SHA1,
                    vk_client_id=VK_ID,
                )

    def test_stable_update_refuses_missing_or_non_increasing_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk, metadata, version = self.fixture(Path(temp))
            for baseline in (None, 10002, 10003, -1, True):
                with self.subTest(baseline=baseline), self.assertRaisesRegex(ValueError, "versionCode baseline"):
                    build_manifest(
                        apk=apk, output_metadata=metadata, version_file=version,
                        source_sha=SHA, api_base_url=ORIGIN, api_fallback_base_url=FALLBACK,
                        repository="spenskoj90-sudo/alpha-0", run_id="12345", run_attempt="2",
                        signer_sha256=SIGNER, expected_signer_sha256=SIGNER, vk_client_id=VK_ID,
                        previous_version_code=baseline, signing_mode="stable-test",
                        workflow_name="Physical Test Update APK",
                    )

    def test_stable_signing_cannot_claim_routine_secret_free_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk, metadata, version = self.fixture(Path(temp))
            with self.assertRaisesRegex(ValueError, "dedicated update workflow"):
                build_manifest(
                    apk=apk,
                    output_metadata=metadata,
                    version_file=version,
                    source_sha=SHA,
                    api_base_url=ORIGIN,
                api_fallback_base_url=FALLBACK,
                    repository="spenskoj90-sudo/alpha-0",
                    run_id="12345",
                    run_attempt="2",
                    signer_sha256=SIGNER,
                    expected_signer_sha256=SIGNER,
                    signing_mode="stable-test",
                )


    def test_stable_update_rejects_signer_lineage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk, metadata, version = self.fixture(Path(temp))
            with self.assertRaisesRegex(ValueError, "pinned update lineage"):
                build_manifest(
                    apk=apk,
                    output_metadata=metadata,
                    version_file=version,
                    source_sha=SHA,
                    api_base_url=ORIGIN,
                api_fallback_base_url=FALLBACK,
                    repository="spenskoj90-sudo/alpha-0",
                    run_id="12345",
                    run_attempt="2",
                    signer_sha256=OTHER_SIGNER,
                    vk_client_id=VK_ID,
                    expected_signer_sha256=SIGNER,
                    signing_mode="stable-test",
                    workflow_name="Physical Test Update APK",
                )

    def test_invalid_vk_client_id_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk, metadata, version = self.fixture(Path(temp))
            with self.assertRaisesRegex(ValueError, "VK client ID"):
                build_manifest(
                    apk=apk,
                    output_metadata=metadata,
                    version_file=version,
                    source_sha=SHA,
                    api_base_url=ORIGIN,
                    api_fallback_base_url=FALLBACK,
                    repository="spenskoj90-sudo/alpha-0",
                    run_id="12345",
                    run_attempt="2",
                    signer_sha256=SIGNER,
                    vk_client_id="not-digits",
                )

    def test_loopback_bytes_in_compiled_dex_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "forbidden loopback"):
                self.create_manifest(Path(temp), dex_suffix=b"http://127.0.0.1:8000")

    def test_wrong_application_id_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "application ID mismatch"):
                self.create_manifest(Path(temp), application_id="com.alpha0.app")


if __name__ == "__main__":
    unittest.main()
