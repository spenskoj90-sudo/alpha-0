#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "branch-hygiene.yml").read_text(encoding="utf-8")
INVENTORY = (ROOT / "docs" / "BRANCH_INVENTORY.md").read_text(encoding="utf-8")


class BranchHygieneWorkflowTests(unittest.TestCase):
    def test_workflow_is_path_scoped_to_protected_main(self) -> None:
        self.assertIn('branches:\n      - main', WORKFLOW)
        self.assertIn('      - ".github/workflows/branch-hygiene.yml"', WORKFLOW)
        self.assertIn('      - "docs/BRANCH_INVENTORY.md"', WORKFLOW)
        self.assertIn('test "$GITHUB_REF" = "refs/heads/main"', WORKFLOW)
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', WORKFLOW)

    def test_only_explicit_reconciled_classes_can_be_deleted(self) -> None:
        self.assertIn('allowed = {"MERGED_EXACT", "PURE_BEHIND", "CONTENT_SUPERSEDED"}', WORKFLOW)
        self.assertIn('if classification == "ACTIVE":', WORKFLOW)
        self.assertIn('if not reason.startswith("RECONCILED:"):', WORKFLOW)
        self.assertNotIn('"UNIQUE_RECONCILE"', WORKFLOW)
        self.assertNotIn('"UNKNOWN"', WORKFLOW)
        self.assertIn('"live tip equals exact PR head"', WORKFLOW)
        self.assertIn("gh api", WORKFLOW)
        self.assertIn("merged_at", WORKFLOW)
        self.assertIn("live_head", WORKFLOW)
        self.assertIn("git merge-base --is-ancestor", WORKFLOW)

    def test_live_tip_and_protected_ref_mutation_abort_before_deletion(self) -> None:
        self.assertIn('if [ "$remote_sha" != "$expected_sha" ]', WORKFLOW)
        self.assertIn("ref mutation detected", WORKFLOW)
        self.assertIn("exact PR-head mismatch", WORKFLOW)
        self.assertIn('if [ "$protected" != "false" ]', WORKFLOW)
        self.assertIn("refusing to delete protected branch", WORKFLOW)
        self.assertIn('git fetch --no-tags origin "refs/heads/$branch"', WORKFLOW)
        self.assertIn('if [ "$fetched_sha" != "$expected_sha" ]', WORKFLOW)
        self.assertIn("fetched ref mutation detected", WORKFLOW)
        self.assertIn('git push origin --delete "$branch"', WORKFLOW)
        self.assertNotIn("--force", WORKFLOW)

    def test_inventory_contains_no_unresolved_branch_state(self) -> None:
        self.assertIn("CONTENT_SUPERSEDED", INVENTORY)
        self.assertIn("MERGED_EXACT", INVENTORY)
        self.assertNotIn("| UNIQUE_RECONCILE |", INVENTORY)
        self.assertNotIn("| UNKNOWN |", INVENTORY)
        for line in INVENTORY.splitlines():
            if "| CONTENT_SUPERSEDED |" in line:
                self.assertIn("| RECONCILED:", line)

    def test_current_merge_branch_cleanup_requires_exact_same_repository_lineage(self) -> None:
        self.assertIn('merge_sha" = "$GITHUB_SHA"', WORKFLOW)
        self.assertIn('base_ref" = "main"', WORKFLOW)
        self.assertIn('head_repo" = "$GITHUB_REPOSITORY"', WORKFLOW)
        self.assertIn('head_ref" != "main"', WORKFLOW)
        self.assertIn('delete_exact_ref "$head_ref" "$head_sha"', WORKFLOW)


if __name__ == "__main__":
    unittest.main()
