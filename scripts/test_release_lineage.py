#!/usr/bin/env python3
import copy
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from release_evidence_entrypoint import enable_supply_chain_evidence
from test_release_evidence import REPO, SHA, VERSION, valid_manifest
from release_lineage import (
    APK_FILE,
    CANDIDATE_FILE,
    PRESECRET_FILE,
    RELEASE_CANDIDATE_WORKFLOW,
    RELEASE_CANDIDATE_WORKFLOW_PATH,
    RELEASE_EVIDENCE_FILE,
    RELEASE_EVIDENCE_WORKFLOW,
    RELEASE_EVIDENCE_WORKFLOW_PATH,
    build_presecret_binding,
    canonical_digest,
    create_candidate_manifest,
    fetch_candidate_package,
    verify_candidate_manifest,
    verify_presecret_binding,
)

SIGNER = "A" * 64


def make_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def release_evidence_fixture(manifest: dict | None = None):
    enable_supply_chain_evidence()
    manifest = manifest or valid_manifest("push")
    archive = make_zip({RELEASE_EVIDENCE_FILE: (json.dumps(manifest, sort_keys=True) + "\n").encode()})
    artifact = {
        "id": 8001,
        "name": f"sentinel-release-evidence-{SHA}",
        "size_in_bytes": len(archive),
        "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
        "expired": False,
        "workflow_run": {"id": 7001, "head_sha": SHA},
    }
    run = {
        "id": 7001,
        "name": RELEASE_EVIDENCE_WORKFLOW,
        "path": RELEASE_EVIDENCE_WORKFLOW_PATH,
        "head_sha": SHA,
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
    }

    def api_get(endpoint: str):
        if "/actions/runs?" in endpoint:
            return {"workflow_runs": [run]}
        if "/actions/runs/7001/artifacts" in endpoint:
            return {"artifacts": [artifact]}
        raise AssertionError(endpoint)

    def downloader(_endpoint: str, _max_bytes: int):
        return archive

    return run, artifact, archive, api_get, downloader


def valid_binding():
    _, _, _, api_get, downloader = release_evidence_fixture()
    return build_presecret_binding(REPO, SHA, VERSION, api_get=api_get, downloader=downloader)


class ReleaseLineageTests(unittest.TestCase):
    def test_presecret_binding_verifies_server_archive_and_manifest(self):
        binding = valid_binding()
        verify_presecret_binding(binding, expected_repository=REPO, expected_sha=SHA, expected_version=VERSION)
        self.assertEqual(binding["source"]["sha"], SHA)
        self.assertFalse(binding["claims"]["signingMaterialAccessed"])
        self.assertEqual(binding["releaseEvidence"]["workflow"]["headBranch"], "main")

    def test_presecret_binding_is_deterministic_for_same_evidence(self):
        first = valid_binding()
        second = valid_binding()
        self.assertEqual(first["bindingDigest"], second["bindingDigest"])
        self.assertEqual(first, second)

    def test_shell_binding_writer_matches_python_canonical_contract(self):
        expected = valid_binding()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / PRESECRET_FILE
            subprocess.run(
                [
                    "bash",
                    "scripts/write_release_presecret_binding.sh",
                    REPO,
                    SHA,
                    VERSION,
                    str(output),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            actual = json.loads(output.read_text(encoding="utf-8"))
        verify_presecret_binding(actual, expected_repository=REPO, expected_sha=SHA, expected_version=VERSION)
        self.assertEqual(actual, expected)

    def test_presecret_rejects_archive_digest_mismatch(self):
        _, artifact, archive, api_get, _ = release_evidence_fixture()
        artifact["digest"] = "sha256:" + ("0" * 64)
        with self.assertRaisesRegex(ValueError, "archive digest"):
            build_presecret_binding(
                REPO,
                SHA,
                VERSION,
                api_get=api_get,
                downloader=lambda *_args: archive,
            )

    def test_presecret_rejects_non_main_run(self):
        run, _, _, api_get, downloader = release_evidence_fixture()
        run["head_branch"] = "feature"
        with self.assertRaisesRegex(ValueError, "no protected-main"):
            build_presecret_binding(REPO, SHA, VERSION, api_get=api_get, downloader=downloader)

    def test_presecret_rejects_pull_request_manifest(self):
        enable_supply_chain_evidence()
        manifest = valid_manifest("pull_request")
        _, _, _, api_get, downloader = release_evidence_fixture(manifest)
        with self.assertRaisesRegex(ValueError, "protected-main push evidence"):
            build_presecret_binding(REPO, SHA, VERSION, api_get=api_get, downloader=downloader)

    def test_candidate_manifest_binds_apk_and_presecret_evidence(self):
        binding = valid_binding()
        apk = b"synthetic signed release apk"
        candidate = create_candidate_manifest(binding, apk, SIGNER)
        verify_candidate_manifest(
            candidate,
            apk,
            expected_binding=binding,
            expected_repository=REPO,
            expected_sha=SHA,
            expected_version=VERSION,
            expected_signer_sha256=SIGNER,
        )
        self.assertTrue(candidate["claims"]["signedReleaseArtifact"])
        self.assertEqual(candidate["presecretBinding"], {"bindingDigest": binding["bindingDigest"]})

    def test_candidate_rejects_apk_tamper(self):
        binding = valid_binding()
        candidate = create_candidate_manifest(binding, b"apk-one", SIGNER)
        with self.assertRaisesRegex(ValueError, "APK metadata mismatch"):
            verify_candidate_manifest(candidate, b"apk-two", expected_binding=binding, expected_signer_sha256=SIGNER)

    def test_candidate_rejects_stale_binding_digest(self):
        binding = valid_binding()
        candidate = create_candidate_manifest(binding, b"apk", SIGNER)
        candidate["presecretBinding"]["bindingDigest"] = "sha256:" + ("2" * 64)
        candidate["candidateDigest"] = canonical_digest(candidate, "candidateDigest")
        with self.assertRaisesRegex(ValueError, "lineage does not match"):
            verify_candidate_manifest(candidate, b"apk", expected_binding=binding, expected_signer_sha256=SIGNER)

    def test_fetch_candidate_verifies_github_archive_and_current_binding(self):
        binding = valid_binding()
        apk = b"signed apk payload"
        candidate = create_candidate_manifest(binding, apk, SIGNER)
        archive = make_zip(
            {
                APK_FILE: apk,
                PRESECRET_FILE: (json.dumps(binding, sort_keys=True) + "\n").encode(),
                CANDIDATE_FILE: (json.dumps(candidate, sort_keys=True) + "\n").encode(),
            }
        )
        run = {
            "id": 9001,
            "name": RELEASE_CANDIDATE_WORKFLOW,
            "path": RELEASE_CANDIDATE_WORKFLOW_PATH,
            "event": "workflow_dispatch",
            "head_branch": "main",
            "status": "completed",
            "conclusion": "success",
            "run_attempt": 1,
        }
        artifact = {
            "id": 9002,
            "name": f"sentinel-release-candidate-{SHA}",
            "size_in_bytes": len(archive),
            "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
            "expired": False,
            "workflow_run": {"id": 9001, "head_sha": "b" * 40},
        }

        def api_get(endpoint: str):
            if "/actions/workflows/release-candidate.yml/runs?" in endpoint:
                return {"workflow_runs": [run]}
            if "/actions/runs/9001/artifacts" in endpoint:
                return {"artifacts": [artifact]}
            raise AssertionError(endpoint)

        fetched, files = fetch_candidate_package(
            REPO,
            SHA,
            VERSION,
            binding,
            SIGNER,
            api_get=api_get,
            downloader=lambda *_args: archive,
        )
        self.assertEqual(fetched["candidateDigest"], candidate["candidateDigest"])
        self.assertEqual(files[APK_FILE], apk)

    def test_fetch_candidate_rejects_tampered_packaged_binding(self):
        binding = valid_binding()
        tampered = copy.deepcopy(binding)
        tampered["bindingDigest"] = "sha256:" + ("3" * 64)
        apk = b"signed apk payload"
        candidate = create_candidate_manifest(binding, apk, SIGNER)
        archive = make_zip(
            {
                APK_FILE: apk,
                PRESECRET_FILE: (json.dumps(tampered, sort_keys=True) + "\n").encode(),
                CANDIDATE_FILE: (json.dumps(candidate, sort_keys=True) + "\n").encode(),
            }
        )
        run = {
            "id": 9001,
            "name": RELEASE_CANDIDATE_WORKFLOW,
            "path": RELEASE_CANDIDATE_WORKFLOW_PATH,
            "event": "workflow_dispatch",
            "head_branch": "main",
            "status": "completed",
            "conclusion": "success",
            "run_attempt": 1,
        }
        artifact = {
            "id": 9002,
            "name": f"sentinel-release-candidate-{SHA}",
            "size_in_bytes": len(archive),
            "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
            "expired": False,
            "workflow_run": {"id": 9001},
        }

        def api_get(endpoint: str):
            if "/actions/workflows/release-candidate.yml/runs?" in endpoint:
                return {"workflow_runs": [run]}
            return {"artifacts": [artifact]}

        with self.assertRaisesRegex(ValueError, "binding digest mismatch"):
            fetch_candidate_package(
                REPO,
                SHA,
                VERSION,
                binding,
                SIGNER,
                api_get=api_get,
                downloader=lambda *_args: archive,
            )

    def test_persisted_binding_contains_no_authenticated_api_metadata(self):
        binding = valid_binding()
        evidence = binding["releaseEvidence"]
        serialized = json.dumps(binding, sort_keys=True)
        self.assertEqual(set(evidence), {"workflow", "artifact"})
        self.assertEqual(
            evidence["artifact"],
            {"name": f"sentinel-release-evidence-{SHA}", "headSha": SHA},
        )
        for field in (
            "generatedAt",
            "runId",
            "runAttempt",
            "artifactId",
            "sizeBytes",
            "workflowMetadataDigest",
            "artifactMetadataDigest",
            "manifestDigest",
        ):
            self.assertNotIn(field, serialized)

    def test_python_lineage_boundary_never_handles_github_credentials_or_presecret_persistence(self):
        source = Path("scripts/release_lineage.py").read_text(encoding="utf-8")
        writer = Path("scripts/write_release_presecret_binding.sh").read_text(encoding="utf-8")
        self.assertNotIn("GITHUB_TOKEN", source)
        self.assertNotIn("GH_TOKEN", source)
        self.assertNotIn("Authorization", source)
        self.assertNotIn("Bearer", source)
        self.assertIn('["gh", "api", "--method", "GET", endpoint]', source)
        self.assertIn("stderr=subprocess.DEVNULL", source)
        self.assertNotIn("print(f", source)
        self.assertNotIn("release-candidate-provenance.json", source)
        self.assertNotIn("_write_presecret_binding", source)
        self.assertNotIn('presecret.add_argument("--output"', source)
        self.assertIn("verify_live_presecret(args.repository, args.sha, version)", source)
        self.assertIn("jq -cSj", writer)
        self.assertIn("sha256sum", writer)
        self.assertNotIn("GITHUB_TOKEN", writer)
        self.assertNotIn("GH_TOKEN", writer)
        self.assertNotIn("secrets.", writer)

    def test_workflows_enforce_presecret_boundary_and_no_release_resigning(self):
        rc = Path(".github/workflows/release-candidate.yml").read_text(encoding="utf-8")
        release = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("source_sha:", rc)
        self.assertIn("needs: presecret", rc)
        presecret_block = rc.split("  presecret:", 1)[1].split("  release-candidate:", 1)[0]
        self.assertNotIn("secrets.", presecret_block)
        self.assertIn("release_lineage.py presecret", presecret_block)
        self.assertIn("write_release_presecret_binding.sh", presecret_block)
        self.assertIn("release_lineage.py verify-binding", presecret_block)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", presecret_block)
        signing_block = rc.split("  release-candidate:", 1)[1]
        self.assertIn("ANDROID_KEYSTORE_BASE64", signing_block)
        self.assertIn("release_lineage.py create-candidate", signing_block)
        self.assertGreaterEqual(rc.count("write_release_presecret_binding.sh"), 2)

        self.assertIn("needs: presecret", release)
        self.assertIn("release_lineage.py fetch-candidate", release)
        self.assertNotIn("ANDROID_KEYSTORE_BASE64", release)
        self.assertNotIn("assembleRelease", release)
        self.assertNotIn("release-candidate-provenance.json", release)
        prepublish = release.split("  presecret:", 1)[1].split("  publish:", 1)[0]
        self.assertNotIn("contents: write", prepublish)
        self.assertNotIn("secrets.", prepublish)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", prepublish)
        self.assertGreaterEqual(release.count("write_release_presecret_binding.sh"), 2)
        self.assertGreaterEqual(release.count("release_lineage.py verify-binding"), 2)


if __name__ == "__main__":
    unittest.main()
