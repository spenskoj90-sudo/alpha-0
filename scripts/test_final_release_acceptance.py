#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import final_release_acceptance as acceptance
import release_lineage

REPOSITORY = "spenskoj90-sudo/alpha-0"
SOURCE_SHA = "1" * 40
VERSION = "1.0.0-rc-test"
SIGNER = "AA" * 32
COMPANION = "sha256:" + "b" * 64
RECORDED_AT = "2026-09-14T19:00:00Z"
ROOT = Path(__file__).resolve().parents[1]


class FinalReleaseAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        binding = release_lineage._binding_from_identity(REPOSITORY, SOURCE_SHA, VERSION)
        self.apk = b"signed-apk-fixture"
        self.candidate = release_lineage.create_candidate_manifest(binding, self.apk, SIGNER)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def gate(self, gate_id: str, marker: str | None = None) -> dict:
        evidence = self.root / f"{gate_id}.json"
        evidence.write_text(json.dumps({"gate": gate_id, "marker": marker or gate_id}), encoding="utf-8")
        return acceptance.build_gate(
            gate_id,
            self.candidate,
            self.apk,
            COMPANION,
            f"env/{gate_id}",
            evidence,
            "application/json",
            RECORDED_AT,
        )

    def manifest(self, profile: str) -> dict:
        gates = [self.gate(gate) for gate in sorted(acceptance.REQUIRED_GATES[profile])]
        return acceptance.build_manifest(profile, self.candidate, self.apk, COMPANION, gates)

    def test_publication_profile_passes(self) -> None:
        manifest = self.manifest("publication")
        acceptance.verify_manifest(
            manifest,
            self.candidate,
            self.apk,
            COMPANION,
            minimum_profile="publication",
            expected_repository=REPOSITORY,
            expected_sha=SOURCE_SHA,
            expected_version=VERSION,
        )

    def test_publication_rejects_missing_physical_gate(self) -> None:
        manifest = self.manifest("publication")
        manifest["gates"] = [gate for gate in manifest["gates"] if gate["id"] != "android-physical"]
        manifest["acceptanceDigest"] = acceptance._canonical_digest(manifest, "acceptanceDigest")
        with self.assertRaisesRegex(ValueError, "missing required"):
            acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION)

    def test_gate_from_other_candidate_is_rejected(self) -> None:
        manifest = self.manifest("publication")
        other_apk = b"different-signed-apk"
        binding = release_lineage._binding_from_identity(REPOSITORY, SOURCE_SHA, VERSION)
        other_candidate = release_lineage.create_candidate_manifest(binding, other_apk, SIGNER)
        evidence = self.root / "mixed.json"
        evidence.write_text("{}", encoding="utf-8")
        mixed_gate = acceptance.build_gate(
            "android-physical",
            other_candidate,
            other_apk,
            COMPANION,
            "env/mixed",
            evidence,
            "application/json",
            RECORDED_AT,
        )
        manifest["gates"] = [mixed_gate if gate["id"] == "android-physical" else gate for gate in manifest["gates"]]
        manifest["acceptanceDigest"] = acceptance._canonical_digest(manifest, "acceptanceDigest")
        with self.assertRaisesRegex(ValueError, "release-byte binding mismatch"):
            acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION)

    def test_companion_archive_drift_is_rejected(self) -> None:
        manifest = self.manifest("publication")
        with self.assertRaisesRegex(ValueError, "release-byte binding mismatch"):
            acceptance.verify_manifest(manifest, self.candidate, self.apk, "sha256:" + "c" * 64)

    def test_deployment_is_stronger_than_publication(self) -> None:
        manifest = self.manifest("publication")
        with self.assertRaisesRegex(ValueError, "weaker than required"):
            acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION, minimum_profile="deployment")
        deployment = self.manifest("deployment")
        acceptance.verify_manifest(deployment, self.candidate, self.apk, COMPANION, minimum_profile="publication")
        acceptance.verify_manifest(deployment, self.candidate, self.apk, COMPANION, minimum_profile="deployment")

    def test_production_traffic_requires_runtime_penetration_gate(self) -> None:
        manifest = self.manifest("production-traffic")
        acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION, minimum_profile="production-traffic")
        manifest["gates"] = [gate for gate in manifest["gates"] if gate["id"] != "runtime-security-penetration"]
        manifest["acceptanceDigest"] = acceptance._canonical_digest(manifest, "acceptanceDigest")
        with self.assertRaisesRegex(ValueError, "missing required"):
            acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION, minimum_profile="production-traffic")

    def test_optional_firebase_gate_is_allowed_but_not_required(self) -> None:
        manifest = self.manifest("publication")
        manifest["gates"].append(self.gate("firebase-test-lab"))
        manifest["acceptanceDigest"] = acceptance._canonical_digest(manifest, "acceptanceDigest")
        acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION)

    def test_claim_tampering_is_rejected(self) -> None:
        manifest = self.manifest("publication")
        manifest["claims"]["productionDeployed"] = True
        manifest["acceptanceDigest"] = acceptance._canonical_digest(manifest, "acceptanceDigest")
        with self.assertRaisesRegex(ValueError, "claims mismatch"):
            acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION)

    def test_acceptance_digest_tampering_is_rejected(self) -> None:
        manifest = self.manifest("publication")
        manifest["acceptanceDigest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            acceptance.verify_manifest(manifest, self.candidate, self.apk, COMPANION)

    def test_gate_schema_rejects_freeform_fields(self) -> None:
        manifest = self.manifest("publication")
        broken = copy.deepcopy(manifest)
        broken["gates"][0]["notes"] = "freeform payload is not allowed"
        broken["acceptanceDigest"] = acceptance._canonical_digest(broken, "acceptanceDigest")
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            acceptance.verify_manifest(broken, self.candidate, self.apk, COMPANION)


class FinalReleaseAcceptanceWorkflowTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_acceptance_workflow_is_no_secret_and_exact_sha_bound(self) -> None:
        workflow = self.read(".github/workflows/final-release-acceptance.yml")
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertIn('test "$GITHUB_SHA" = "$SOURCE_SHA"', workflow)
        self.assertIn("verify_release_upstream_attestations.sh", workflow)
        self.assertIn("verify signed candidate artifact attestations".lower(), workflow.lower())
        self.assertIn("actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("attestations: write", workflow)

    def test_release_publication_requires_final_acceptance(self) -> None:
        workflow = self.read(".github/workflows/release.yml")
        self.assertIn("verify_final_release_acceptance_live.sh", workflow)
        self.assertIn("publication", workflow)
        self.assertIn("final-release-acceptance.json", workflow)
        self.assertIn("EXPECTED_ACCEPTANCE_SHA256", workflow)
        self.assertIn("release-input/final-release-acceptance.json", workflow)

    def test_remote_rollout_is_owner_dispatch_only_and_stronger_profile(self) -> None:
        workflow = self.read(".github/workflows/deploy.yml")
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("needs.deployment-acceptance.result == 'success'", workflow)
        self.assertIn("verify_final_release_acceptance_live.sh", workflow)
        self.assertIn("deployment", workflow)
        self.assertNotIn('default: "latest"', workflow)

    def test_live_verifier_rechecks_candidate_package_and_acceptance_attestations(self) -> None:
        helper = self.read("scripts/verify_final_release_acceptance_live.sh")
        for required in (
            "verify_release_evidence_attestation.sh",
            "release_lineage.py fetch-candidate",
            "verify_github_attestation.sh",
            "verify_release_upstream_attestations.sh",
            "verify_final_release_acceptance_attestation.sh",
            "final_release_acceptance.py verify",
        ):
            self.assertIn(required, helper)


if __name__ == "__main__":
    unittest.main()
