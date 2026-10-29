#!/usr/bin/env python3
"""Signed physical-test version allocation must remain monotonic for decades."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("physical_test_version.py")


class PhysicalTestVersionTests(unittest.TestCase):
    def allocate(self, previous: object, run_number: object):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--previous-version-code", str(previous),
             "--workflow-run-number", str(run_number)],
            capture_output=True, text=True,
        )

    def test_clean_first_install_keeps_version_headroom(self):
        result = self.allocate(0, 1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(result.stdout), 100000001)

    def test_future_workflow_runs_auto_increment_even_with_stale_owner_baseline(self):
        first = self.allocate(0, 10)
        second = self.allocate(0, 11)
        self.assertEqual(int(first.stdout), 100000010)
        self.assertEqual(int(second.stdout), 100000011)

    def test_confirmed_old_version_takes_precedence_even_after_workflow_reset(self):
        result = self.allocate(1790954700, 1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(result.stdout), 1790954701)

    def test_new_install_code_leaves_years_of_update_room(self):
        result = self.allocate(0, 20000)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(int(result.stdout), 200000000)

    def test_malformed_and_overflow_fail_closed(self):
        for previous, run in [
            ("", 1), ("01", 1), ("-1", 1), ("1e9", 1), ("2100000000", 1),
            (0, 0), (0, -1), (0, "01"), (0, ""), (0, "2000000001"),
        ]:
            with self.subTest(previous=previous, run=run):
                result = self.allocate(previous, run)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_maximum_code_and_next_update(self):
        self.assertEqual(int(self.allocate(2099999999, 1).stdout), 2100000000)
        self.assertNotEqual(self.allocate(2100000000, 1).returncode, 0)


if __name__ == "__main__":
    unittest.main()
