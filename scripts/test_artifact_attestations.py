#!/usr/bin/env python3
from pathlib import Path
import unittest


ATTEST_PIN = "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4"
DOWNLOAD_PIN = "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1"


class ArtifactAttestationContractTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def test_verifier_enforces_exact_actor_source_and_runner_policy(self):
        verifier = self.read("scripts/verify_github_attestation.sh")
        for required in (
            'gh attestation verify "$artifact"',
            '--repo "$repository"',
            '--signer-workflow "$repository/$workflow_path"',
            '--source-digest "$source_sha"',
            '--source-ref "$source_ref"',
            '--deny-self-hosted-runners',
        ):
            self.assertIn(required, verifier)
        self.assertNotIn("GITHUB_TOKEN", verifier)
        self.assertNotIn("GH_TOKEN", verifier)

    def test_supply_chain_attestation_is_main_only_and_separate_from_build(self):
        workflow = self.read(".github/workflows/supply-chain-evidence.yml")
        self.assertIn("  attest-supply-chain:", workflow)
        block = workflow.split("  attest-supply-chain:", 1)[1]
        self.assertIn("github.event_name == 'push'", block)
        self.assertIn("github.ref == 'refs/heads/main'", block)
        self.assertIn("needs: supply-chain-evidence", block)
        self.assertIn("id-token: write", block)
        self.assertIn("attestations: write", block)
        self.assertIn("artifact-metadata: write", block)
        self.assertIn(ATTEST_PIN, block)
        self.assertIn(DOWNLOAD_PIN, block)
        self.assertNotIn("secrets.", block)
        build_block = workflow.split("  supply-chain-evidence:", 1)[1].split("  attest-supply-chain:", 1)[0]
        self.assertNotIn("id-token: write", build_block)
        self.assertNotIn("attestations: write", build_block)

    def test_packaged_companion_attestation_is_main_only_and_separate(self):
        workflow = self.read(".github/workflows/packaged-companion.yml")
        self.assertIn("  attest-packaged-companion:", workflow)
        package_block = workflow.split("  packaged-companion:", 1)[1].split("  attest-packaged-companion:", 1)[0]
        self.assertIn("retention-days: 90", package_block)
        self.assertNotIn("retention-days: 14", package_block)
        block = workflow.split("  attest-packaged-companion:", 1)[1]
        self.assertIn("github.event_name == 'push'", block)
        self.assertIn("github.ref == 'refs/heads/main'", block)
        self.assertIn("needs: packaged-companion", block)
        self.assertIn("id-token: write", block)
        self.assertIn("attestations: write", block)
        self.assertIn(ATTEST_PIN, block)
        self.assertNotIn("secrets.", block)

    def test_release_evidence_verifies_upstream_attestations_before_upload_and_is_attested(self):
        workflow = self.read(".github/workflows/release-evidence.yml")
        verification = workflow.find("Verify protected-main upstream artifact attestations")
        upload = workflow.find("Upload exact-SHA release evidence")
        self.assertGreaterEqual(verification, 0)
        self.assertGreater(upload, verification)
        self.assertIn("verify_release_upstream_attestations.sh", workflow)
        self.assertIn("attestations: read", workflow)
        self.assertIn("  attest-release-evidence:", workflow)
        attest_block = workflow.split("  attest-release-evidence:", 1)[1]
        self.assertIn("github.event_name == 'push'", attest_block)
        self.assertIn("needs: release-evidence", attest_block)
        self.assertIn(ATTEST_PIN, attest_block)
        self.assertNotIn("secrets.", attest_block)

    def test_release_candidate_requires_dispatch_commit_identity_and_attests_after_signing(self):
        workflow = self.read(".github/workflows/release-candidate.yml")
        self.assertIn('test "$GITHUB_SHA" = "$SOURCE_SHA"', workflow)
        self.assertIn("  attest-release-candidate:", workflow)
        signing = workflow.split("  release-candidate:", 1)[1].split("  attest-release-candidate:", 1)[0]
        attest = workflow.split("  attest-release-candidate:", 1)[1]
        self.assertIn("ANDROID_KEYSTORE_BASE64", signing)
        self.assertIn("id: hashes", signing)
        self.assertIn("needs: release-candidate", attest)
        self.assertIn("id-token: write", attest)
        self.assertIn("attestations: write", attest)
        self.assertIn(ATTEST_PIN, attest)
        self.assertNotIn("secrets.", attest)

    def test_publication_verifies_release_and_candidate_attestations_before_write_authority(self):
        workflow = self.read(".github/workflows/release.yml")
        presecret = workflow.split("  presecret:", 1)[1].split("  verify-candidate:", 1)[0]
        verify = workflow.split("  verify-candidate:", 1)[1].split("  publish:", 1)[0]
        publish = workflow.split("  publish:", 1)[1]
        self.assertIn("verify_release_evidence_attestation.sh", presecret)
        self.assertIn("attestations: read", presecret)
        self.assertIn("verify_github_attestation.sh", verify)
        for subject in (
            "release-input/app-release.apk",
            "release-input/release-candidate.json",
            "release-input/release-presecret-binding.json",
        ):
            self.assertIn(subject, verify)
        self.assertIn(".github/workflows/release-candidate.yml", verify)
        self.assertIn("refs/heads/main", verify)
        self.assertNotIn("contents: write", presecret + verify)
        self.assertIn("contents: write", publish)
        self.assertNotIn("actions/attest@", publish)
        self.assertNotIn("id-token: write", publish)

    def test_release_attestation_helpers_are_fail_closed(self):
        upstream = self.read("scripts/verify_release_upstream_attestations.sh")
        release = self.read("scripts/verify_release_evidence_attestation.sh")
        self.assertIn('event="$(jq -er', upstream)
        self.assertIn('[ "$event" = "push" ]', upstream)
        self.assertIn("supply_chain_evidence.py verify", upstream)
        self.assertGreaterEqual(upstream.count("verify_github_attestation.sh"), 2)
        self.assertIn("head_sha=$source_sha", release)
        self.assertIn("status == \"completed\"", release)
        self.assertIn("conclusion == \"success\"", release)
        self.assertIn("verify_github_attestation.sh", release)


if __name__ == "__main__":
    unittest.main()
