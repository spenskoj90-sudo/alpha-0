from __future__ import annotations

import copy
import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sentinel_orchestration", ROOT / "scripts/sentinel_orchestration.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Harness Test")
        self.git("config", "user.email", "harness@example.invalid")
        (self.root / "AGENTS.md").write_text("governance\n")
        (self.root / "docs").mkdir()
        (self.root / "docs/TASKS.md").write_text("- [ ] **#314** physical\n- [ ] **#375** visual\n")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD")
        self.patch = patch.object(module, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.manifest = {
            "schema": "sentinel.orchestration-lanes.v1", "baseSha": self.sha,
            "lanes": [self.lane("governance", "repository_contract", "AGENTS.md"),
                      self.lane("acceptance", "acceptance_contract", "docs/TASKS.md")],
        }

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def lane(self, lane_id, reader, path):
        return {"id": lane_id, "baseSha": self.sha, "mode": "read_only", "reader": reader,
                "ownedPaths": [path], "acceptanceChecks": ["file digest"], "dependencies": []}

    def test_two_readers_return_source_bound_evidence(self):
        result = module.run(self.manifest)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["baseSha"], self.sha)
        self.assertEqual(result["laneCount"], 2)
        self.assertEqual(result["parallelWorkers"], 2)
        self.assertEqual(result["lanes"][0]["result"]["digests"]["AGENTS.md"],
                         hashlib.sha256(b"governance\n").hexdigest())
        self.assertEqual(result["lanes"][1]["result"]["activeAcceptanceIssues"], [314, 375])
        self.assertIsNone(result["metrics"]["tokenOrCreditUse"])

    def test_dirty_checkout_cannot_change_exact_sha_evidence(self):
        (self.root / "AGENTS.md").write_text("uncommitted governance\n")
        (self.root / "docs/TASKS.md").write_text("- [ ] **#999** uncommitted\n")
        result = module.run(self.manifest)
        self.assertEqual(result["lanes"][0]["result"]["digests"]["AGENTS.md"],
                         hashlib.sha256(b"governance\n").hexdigest())
        self.assertEqual(result["lanes"][1]["result"]["activeAcceptanceIssues"], [314, 375])

    def test_commit_replacement_cannot_substitute_source(self):
        (self.root / "AGENTS.md").write_text("replacement\n")
        self.git("add", "AGENTS.md")
        self.git("commit", "-qm", "replacement")
        replacement = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", self.sha)
        self.git("replace", self.sha, replacement)
        result = module.run(self.manifest)
        self.assertEqual(result["lanes"][0]["result"]["digests"]["AGENTS.md"],
                         hashlib.sha256(b"governance\n").hexdigest())

    def test_blob_replacement_cannot_substitute_source(self):
        original = self.git("rev-parse", "HEAD:AGENTS.md")
        (self.root / "replacement.txt").write_text("replacement\n")
        replacement = self.git("hash-object", "-w", "replacement.txt")
        self.git("replace", original, replacement)
        result = module.run(self.manifest)
        self.assertEqual(result["lanes"][0]["result"]["digests"]["AGENTS.md"],
                         hashlib.sha256(b"governance\n").hexdigest())

    def test_oversized_evidence_file_is_rejected(self):
        (self.root / "large.txt").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        self.git("add", "large.txt")
        self.git("commit", "-qm", "oversized evidence")
        self.manifest["baseSha"] = self.git("rev-parse", "HEAD")
        for lane in self.manifest["lanes"]:
            lane["baseSha"] = self.manifest["baseSha"]
        self.manifest["lanes"][0]["ownedPaths"] = ["large.txt"]
        with self.assertRaises(module.ManifestError):
            module.run(self.manifest)

    def test_excessive_owned_paths_are_rejected(self):
        self.manifest["lanes"][0]["ownedPaths"] = ["AGENTS.md"] * 33
        with self.assertRaises(module.ManifestError):
            module.validate_manifest(self.manifest)

    def test_untracked_files_are_not_source_evidence(self):
        (self.root / "untracked.txt").write_text("local only")
        self.manifest["lanes"][0]["ownedPaths"] = ["untracked.txt"]
        with self.assertRaises(module.ManifestError):
            module.run(self.manifest)

    def test_symlink_is_not_a_source_file(self):
        (self.root / "alias").symlink_to("AGENTS.md")
        self.git("add", "alias")
        self.git("commit", "-qm", "symlink")
        self.manifest["baseSha"] = self.git("rev-parse", "HEAD")
        for lane in self.manifest["lanes"]:
            lane["baseSha"] = self.manifest["baseSha"]
        self.manifest["lanes"][0]["ownedPaths"] = ["alias"]
        with self.assertRaises(module.ManifestError):
            module.run(self.manifest)

    def test_stale_head_is_rejected(self):
        self.manifest["baseSha"] = "a" * 40
        for lane in self.manifest["lanes"]:
            lane["baseSha"] = "a" * 40
        with self.assertRaises(module.ManifestError):
            module.run(self.manifest)

    def test_dependencies_run_before_their_consumers(self):
        self.manifest["lanes"][1]["dependencies"] = ["governance"]
        self.manifest["lanes"].reverse()
        result = module.run(self.manifest)
        self.assertEqual([lane["id"] for lane in result["lanes"]], ["governance", "acceptance"])

    def test_invalid_manifest_fails_closed(self):
        for value in [None, [], "invalid", {}, {"schema": "invalid"}]:
            with self.subTest(value=value), self.assertRaises(module.ManifestError):
                module.validate_manifest(value)

    def test_invalid_lane_contracts_are_rejected(self):
        mutations = [
            ("id", " governance "), ("id", 42), ("baseSha", "b" * 40),
            ("mode", "automatic"), ("reader", "shell"), ("ownedPaths", []),
            ("ownedPaths", ["../outside"]), ("ownedPaths", ["/absolute"]),
            ("acceptanceChecks", []), ("dependencies", ["missing"]),
            ("dependencies", ["governance"]), ("worktree", "../other"),
        ]
        for field, value in mutations:
            manifest = copy.deepcopy(self.manifest)
            manifest["lanes"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(module.ManifestError):
                module.validate_manifest(manifest)

    def test_duplicate_ids_and_dependency_cycles_are_rejected(self):
        duplicate = copy.deepcopy(self.manifest)
        duplicate["lanes"][1]["id"] = "governance"
        with self.assertRaises(module.ManifestError):
            module.validate_manifest(duplicate)
        self.manifest["lanes"][0]["dependencies"] = ["acceptance"]
        self.manifest["lanes"][1]["dependencies"] = ["governance"]
        with self.assertRaises(module.ManifestError):
            module.validate_manifest(self.manifest)

    def test_write_execution_is_always_refused(self):
        lane = self.manifest["lanes"][0]
        lane.update(mode="write", branch="worker/test", worktree="../worker")
        module.validate_manifest(self.manifest)
        with self.assertRaises(module.ManifestError):
            module.run(self.manifest)

    def test_mutable_worktree_aliases_are_rejected(self):
        for lane, path in zip(self.manifest["lanes"], ["../worker", "../worker/."]):
            lane.update(mode="write", branch="worker/" + lane["id"], worktree=path)
        with self.assertRaises(module.ManifestError):
            module.validate_manifest(self.manifest)

    def test_shared_repository_and_main_branch_aliases_are_rejected(self):
        for path, branch in [(str(self.root), "worker/test"), ("./docs/..", "worker/test"),
                             ("../worker", "refs/heads/main")]:
            manifest = copy.deepcopy(self.manifest)
            manifest["lanes"][0].update(mode="write", branch=branch, worktree=path)
            with self.subTest(path=path, branch=branch), self.assertRaises(module.ManifestError):
                module.validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
