#!/usr/bin/env python3
"""Regression coverage for the cross-workflow physical-test version boundary."""
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("physical_test_version.py")


class PhysicalTestVersionTests(unittest.TestCase):
    def allocate(self, previous, epoch):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--previous-version-code", str(previous), "--epoch-seconds", str(epoch)],
            capture_output=True, text=True,
        )

    def test_first_stable_workflow_is_above_existing_diagnostic_install(self):
        result = self.allocate(100000525, 1790954640)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(result.stdout), 1790954640)

    def test_clock_rollback_still_advances_past_confirmed_distributed_version(self):
        result = self.allocate(1790954700, 1790954640)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(result.stdout), 1790954701)

    def test_malformed_or_out_of_range_inputs_fail_closed(self):
        for previous, epoch in [("", 1790954640), ("1e9", 1790954640), ("-1", 1790954640),
                                ("01", 1790954640), (2100000000, 1790954640),
                                (100000525, 2100000001), (100000525, -1)]:
            with self.subTest(previous=previous, epoch=epoch):
                result = self.allocate(previous, epoch)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_android_maximum_is_accepted_only_without_overflow(self):
        result = self.allocate(2099999999, 1790954640)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(result.stdout), 2100000000)

    def test_new_identity_requires_an_explicit_zero_baseline(self):
        result = self.allocate(0, 1790954640)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(result.stdout), 1790954640)


if __name__ == "__main__":
    unittest.main()
