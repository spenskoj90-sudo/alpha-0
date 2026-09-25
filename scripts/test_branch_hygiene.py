#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "branch-hygiene.yml").read_text(encoding="utf-8")


class BranchHygieneWorkflowTests(unittest.TestCase):
    def test_workflow_is_one_shot_path_scoped_to_protected_main(self) -> None:
        self.assertIn('branches:\n      - main', WORKFLOW)
        self.assertIn('paths:\n      - ".github/workflows/branch-hygiene.yml"', WORKFLOW)
        self.assertIn('test "$GITHUB_REF" = "refs/heads/main"', WORKFLOW)
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', WORKFLOW)

    def test_only_exact_merged_or_ancestor_safe_classes_can_be_deleted(self) -> None:
        self.assertIn('classification not in {"MERGED", "PURE_BEHIND"}', WORKFLOW)
        self.assertNotIn('"CONTENT_SUPERSEDED"', WORKFLOW)
        self.assertNotIn('"UNIQUE_MUST_PRESERVE"', WORKFLOW)
        self.assertNotIn('"ACTIVE_RECENT"', WORKFLOW)
        self.assertIn('"exact merged PR head"', WORKFLOW)
        self.assertIn("gh api", WORKFLOW)
        self.assertIn("merged_at", WORKFLOW)
        self.assertIn("live_head", WORKFLOW)
        self.assertIn("git merge-base --is-ancestor", WORKFLOW)

    def test_live_tip_mutation_aborts_before_deletion(self) -> None:
        self.assertIn("ref mutation detected", WORKFLOW)
        self.assertIn("exact PR-head mismatch", WORKFLOW)
        self.assertIn('git push origin --delete "$branch"', WORKFLOW)
        self.assertNotIn("--force", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
