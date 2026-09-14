#!/usr/bin/env python3
import unittest

import release_evidence
from release_evidence_entrypoint import SUPPLY_CHAIN_SPEC, SUPPLY_CHAIN_WORKFLOW, enable_supply_chain_evidence
from test_release_evidence import SHA, valid_manifest


class SupplyChainReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        enable_supply_chain_evidence()

    def test_supply_chain_workflow_is_required_for_push_and_pr(self):
        for event in ("push", "pull_request"):
            self.assertEqual(release_evidence.WORKFLOW_SPECS[event][SUPPLY_CHAIN_WORKFLOW], SUPPLY_CHAIN_SPEC)
            manifest = valid_manifest(event)
            release_evidence.verify_manifest(manifest)

    def test_missing_supply_chain_workflow_fails(self):
        manifest = valid_manifest("push")
        manifest["workflows"] = [item for item in manifest["workflows"] if item["name"] != SUPPLY_CHAIN_WORKFLOW]
        manifest["evidenceDigest"] = release_evidence.canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "workflow evidence set mismatch"):
            release_evidence.verify_manifest(manifest)

    def test_missing_supply_chain_artifact_fails(self):
        manifest = valid_manifest("push")
        workflow = next(item for item in manifest["workflows"] if item["name"] == SUPPLY_CHAIN_WORKFLOW)
        workflow["artifacts"] = []
        manifest["evidenceDigest"] = release_evidence.canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "required artifact evidence missing"):
            release_evidence.verify_manifest(manifest)

    def test_supply_chain_artifact_is_exact_sha_bound(self):
        manifest = valid_manifest("push")
        workflow = next(item for item in manifest["workflows"] if item["name"] == SUPPLY_CHAIN_WORKFLOW)
        artifact = workflow["artifacts"][0]
        self.assertEqual(artifact["name"], f"sentinel-supply-chain-evidence-{SHA}")
        artifact["headSha"] = "c" * 40
        manifest["evidenceDigest"] = release_evidence.canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "invalid artifact evidence"):
            release_evidence.verify_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
