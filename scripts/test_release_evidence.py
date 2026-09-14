#!/usr/bin/env python3
import copy
import unittest

from release_evidence import WORKFLOW_SPECS, canonical_digest, verify_manifest

SHA = "a" * 40
REPO = "spenskoj90-sudo/alpha-0"
VERSION = "1.0-test"


def valid_manifest(event: str = "push") -> dict:
    workflows = []
    artifact_id = 1000
    job_id = 2000
    run_id = 3000
    for workflow_name in sorted(WORKFLOW_SPECS[event]):
        spec = WORKFLOW_SPECS[event][workflow_name]
        jobs = []
        for job_name in sorted(spec["jobs"]):
            job_id += 1
            jobs.append(
                {
                    "id": job_id,
                    "name": job_name,
                    "status": "completed",
                    "conclusion": "success",
                }
            )
        artifacts = []
        for template in spec["artifacts"]:
            artifact_id += 1
            artifacts.append(
                {
                    "id": artifact_id,
                    "name": template.format(sha=SHA),
                    "sizeBytes": 123,
                    "digest": "sha256:" + ("b" * 64),
                    "expired": False,
                    "headSha": SHA,
                    "expiresAt": "2099-01-01T00:00:00Z",
                    "required": True,
                }
            )
        run_id += 1
        workflows.append(
            {
                "name": workflow_name,
                "runId": run_id,
                "runAttempt": 1,
                "event": event,
                "headSha": SHA,
                "status": "completed",
                "conclusion": "success",
                "htmlUrl": f"https://github.com/example/run/{run_id}",
                "jobs": jobs,
                "artifacts": artifacts,
            }
        )
    checks = []
    if event == "pull_request":
        checks.append(
            {
                "id": 9999,
                "name": "CodeQL",
                "appSlug": "github-advanced-security",
                "status": "completed",
                "conclusion": "success",
                "headSha": SHA,
                "htmlUrl": "https://github.com/example/check/9999",
            }
        )
    manifest = {
        "schema": "sentinel.release-evidence.v1",
        "status": "PASS",
        "generatedAt": "2026-09-14T00:00:00Z",
        "source": {
            "repository": REPO,
            "sha": SHA,
            "version": VERSION,
            "event": event,
        },
        "claims": {
            "signedReleaseArtifact": False,
            "releasePublished": False,
            "productionDeployed": False,
            "externalEnvironmentAcceptanceSatisfied": False,
        },
        "workflows": workflows,
        "externalChecks": checks,
    }
    manifest["evidenceDigest"] = canonical_digest(manifest)
    return manifest


class ReleaseEvidenceTests(unittest.TestCase):
    def test_valid_push_manifest(self):
        verify_manifest(
            valid_manifest("push"),
            expected_repository=REPO,
            expected_sha=SHA,
            expected_version=VERSION,
        )

    def test_valid_pull_request_requires_android_ci_and_ghas_codeql(self):
        manifest = valid_manifest("pull_request")
        names = {workflow["name"] for workflow in manifest["workflows"]}
        self.assertIn("ALPHA-0 Android CI", names)
        verify_manifest(manifest)

    def test_digest_tampering_fails(self):
        manifest = valid_manifest()
        manifest["generatedAt"] = "2026-09-15T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            verify_manifest(manifest)

    def test_stale_artifact_sha_fails_even_with_recomputed_digest(self):
        manifest = valid_manifest()
        artifact = next(
            artifact
            for workflow in manifest["workflows"]
            for artifact in workflow["artifacts"]
        )
        artifact["headSha"] = "c" * 40
        manifest["evidenceDigest"] = canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "invalid artifact evidence"):
            verify_manifest(manifest)

    def test_missing_required_job_fails(self):
        manifest = valid_manifest()
        build = next(workflow for workflow in manifest["workflows"] if workflow["name"] == "Build & Test")
        build["jobs"] = build["jobs"][1:]
        manifest["evidenceDigest"] = canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "job evidence set mismatch"):
            verify_manifest(manifest)

    def test_preflight_cannot_claim_signed_or_published_release(self):
        manifest = valid_manifest()
        manifest["claims"]["signedReleaseArtifact"] = True
        manifest["evidenceDigest"] = canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "must not claim"):
            verify_manifest(manifest)

    def test_pr_without_external_codeql_fails(self):
        manifest = valid_manifest("pull_request")
        manifest["externalChecks"] = []
        manifest["evidenceDigest"] = canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "Advanced Security CodeQL"):
            verify_manifest(manifest)

    def test_missing_required_artifact_fails(self):
        manifest = valid_manifest()
        packaged = next(
            workflow for workflow in manifest["workflows"] if workflow["name"] == "Packaged Companion Host"
        )
        packaged["artifacts"] = []
        manifest["evidenceDigest"] = canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "required artifact evidence missing"):
            verify_manifest(manifest)

    def test_workflow_failure_fails(self):
        manifest = valid_manifest()
        manifest["workflows"][0]["conclusion"] = "failure"
        manifest["evidenceDigest"] = canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, "invalid workflow evidence"):
            verify_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
