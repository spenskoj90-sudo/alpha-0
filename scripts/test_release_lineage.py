#!/usr/bin/env python3
import copy
import hashlib
import io
import json
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
        self.assertEqual(candidate["presecretBinding"]["bindingDigest"], binding["bindingDigest"])

    def test_candidate_rejects_apk_tamper(self):
        binding = valid_binding()
        candidate = create_candidate_manifest(binding, b"apk-one", SIGNER)
        with self.assertRaisesRegex(ValueError, "APK metadata mismatch"):
            verify_candidate_manifest(candidate, b"apk-two", expected_binding=binding, expected_signer_sha256=SIGNER)

    def test_candidate_rejects_stale_binding(self):
        binding = valid_binding()
        candidate = create_candidate_manifest(binding, b"apk", SIGNER)
        changed = copy.deepcopy(binding)
        changed["releaseEvidence"]["workflowMetadataDigest"] = "sha256:" + ("2" * 64)
        changed["bindingDigest"] = canonical_digest(changed, "bindingDigest")
        with self.assertRaisesRegex(ValueError, "lineage does not match"):
            verify_candidate_manifest(candidate, b"apk", expected_binding=changed, expected_signer_sha256=SIGNER)

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

        fetched, files, provenance = fetch_candidate_package(
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
        self.assertEqual(provenance["artifactDigest"], artifact["digest"])

    def test_fetch_candidate_rejects_packaged_stale_binding(self):
        binding = valid_binding()
        stale = copy.deepcopy(binding)
        stale["releaseEvidence"]["artifactMetadataDigest"] = "sha256:" + ("3" * 64)
        stale["bindingDigest"] = canonical_digest(stale, "bindingDigest")
        apk = b"signed apk payload"
        candidate = create_candidate_manifest(stale, apk, SIGNER)
        archive = make_zip(
            {
                APK_FILE: apk,
                PRESECRET_FILE: (json.dumps(stale, sort_keys=True) + "\n").encode(),
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

        with self.assertRaisesRegex(ValueError, "stale or different"):
            fetch_candidate_package(
                REPO,
                SHA,
                VERSION,
                binding,
                SIGNER,
                api_get=api_get,
                downloader=lambda *_args: archive,
            )

    def test_python_lineage_boundary_never_handles_github_credentials(self):
        source = Path("scripts/release_lineage.py").read_text(encoding="utf-8")
        self.assertNotIn("GITHUB_TOKEN", source)
        self.assertNotIn("GH_TOKEN", source)
        self.assertNotIn("Authorization", source)
        self.assertNotIn("Bearer", source)
        self.assertIn('["gh", "api", "--method", "GET", endpoint]', source)
        self.assertIn("stderr=subprocess.DEVNULL", source)
        self.assertNotIn("bindingDigest']}", source)
        self.assertNotIn("candidateDigest']}", source)

    def test_workflows_enforce_presecret_boundary_and_no_release_resigning(self):
        rc = Path(".github/workflows/release-candidate.yml").read_text(encoding="utf-8")
        release = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("source_sha:", rc)
        self.assertIn("needs: presecret", rc)
        presecret_block = rc.split("  presecret:", 1)[1].split("  release-candidate:", 1)[0]
        self.assertNotIn("secrets.", presecret_block)
        self.assertIn("release_lineage.py presecret", presecret_block)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", presecret_block)
        signing_block = rc.split("  release-candidate:", 1)[1]
        self.assertIn("ANDROID_KEYSTORE_BASE64", signing_block)
        self.assertIn("release_lineage.py create-candidate", signing_block)

        self.assertIn("needs: presecret", release)
        self.assertIn("release_lineage.py fetch-candidate", release)
        self.assertNotIn("ANDROID_KEYSTORE_BASE64", release)
        self.assertNotIn("assembleRelease", release)
        prepublish = release.split("  presecret:", 1)[1].split("  publish:", 1)[0]
        self.assertNotIn("contents: write", prepublish)
        self.assertNotIn("secrets.", prepublish)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", prepublish)


if __name__ == "__main__":
    unittest.main()
