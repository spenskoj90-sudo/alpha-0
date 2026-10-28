#!/usr/bin/env python3
"""Regression tests for the non-destructive branch review boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github/workflows/branch-hygiene.yml').read_text(encoding='utf-8')


class BranchHygieneWorkflowTests(unittest.TestCase):
    def test_review_has_no_deletion_or_write_authority(self) -> None:
        self.assertIn('contents: read', WORKFLOW)
        self.assertNotIn(': write', WORKFLOW)
        self.assertIn('persist-credentials: false', WORKFLOW)
        for forbidden in ('git push', '--delete', 'delete_exact_ref', 'gh api -X', 'pull_request_target'):
            self.assertNotIn(forbidden, WORKFLOW)

    def test_main_manual_and_exact_source_are_preserved(self) -> None:
        self.assertIn('workflow_dispatch:', WORKFLOW)
        self.assertIn('branches:\n      - main', WORKFLOW)
        self.assertIn('cancel-in-progress: false', WORKFLOW)
        self.assertIn('ref: ${{ github.sha }}', WORKFLOW)
        self.assertIn('test "$GITHUB_REF" = "refs/heads/main"', WORKFLOW)
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', WORKFLOW)

    def run_review(self, *, fail: bool = False) -> subprocess.CompletedProcess[str]:
        marker = '      - name: Read live branch inventory without mutation\n'
        self.assertIn(marker, WORKFLOW)
        step = WORKFLOW.split(marker, 1)[1].split('\n      - name:', 1)[0]
        script = textwrap.dedent(step.split('        run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            fake = temp / 'gh'
            fake.write_text('#!/usr/bin/env python3\nimport os, sys\n'
                            'expected = ["api", "--method", "GET", "--paginate", "--slurp", '
                            '"repos/example/project/branches?per_page=100"]\n'
                            'assert sys.argv[1:] == expected, sys.argv\n'
                            'if os.environ.get("FAIL_GH") == "1": sys.exit(23)\n'
                            'print(os.environ["BRANCH_FIXTURE"])\n', encoding='utf-8')
            fake.chmod(0o755)
            fixture = [[{'name': 'main', 'commit': {'sha': 'a' * 40}, 'protected': True}],
                       [{'name': 'feature/$(touch SHOULD_NOT_EXIST)',
                         'commit': {'sha': 'b' * 40}, 'protected': False}]]
            env = dict(os.environ, PATH=directory + os.pathsep + os.environ['PATH'],
                       RUNNER_TEMP=directory, GITHUB_REPOSITORY='example/project',
                       BRANCH_FIXTURE=json.dumps(fixture), FAIL_GH='1' if fail else '0')
            result = subprocess.run(['bash', '-c', script], env=env, cwd=directory,
                                    capture_output=True, text=True, check=False)
            self.assertFalse((temp / 'SHOULD_NOT_EXIST').exists())
            return result

    def test_all_pages_are_reported_as_review_required_without_shell_execution(self) -> None:
        result = self.run_review()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')
        self.assertEqual(report['deleted'], 0)
        self.assertEqual(len(report['branches']), 2)
        self.assertTrue(report['branches'][0]['protected'])
        self.assertEqual(report['branches'][1]['name'], 'feature/$(touch SHOULD_NOT_EXIST)')

    def test_read_failure_is_not_success_or_permission_to_delete(self) -> None:
        result = self.run_review(fail=True)
        self.assertEqual(result.returncode, 23)
        self.assertNotIn('REVIEW_REQUIRED', result.stdout)


if __name__ == '__main__':
    unittest.main()

