#!/usr/bin/env python3
"""Synthetic regression for strict debug emulator JUnit XML accounting."""
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from verify_android_instrumentation_xml import DEBUG_VARIANT_SKIPS, verify


ASSUME = ("org.junit.AssumptionViolatedException: got: <false>, expected: is <true>\n"
          "\tat org.junit.Assume.assumeThat(Assume.java:106)\n"
          "\tat org.junit.Assume.assumeTrue(Assume.java:50)\n")


class InstrumentationReceiptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def report(self, gate="expected", other="pass", missing=None, duplicate=False):
        root = ET.Element("testsuite")
        for cls, name in sorted(DEBUG_VARIANT_SKIPS):
            if (cls, name) == missing:
                continue
            c = ET.SubElement(root, "testcase", classname=cls, name=name)
            if gate != "pass":
                tag = "error" if gate == "error" else "failure"
                outcome = ET.SubElement(c, tag)
                outcome.text = ASSUME if gate == "expected" else "org.junit.AssertionError: 1 != 2"
        extra = ET.SubElement(root, "testcase", classname="x.NonGatedTest", name="mustPass")
        if other != "pass":
            tag = other
            e = ET.SubElement(extra, tag)
            e.text = "org.junit.AssertionError" if tag == "failure" else "diagnostic"
        for index in range(45):
            ET.SubElement(root, "testcase", classname="x.NormalRegression", name=f"test{index:03d}")
        if duplicate:
            ET.SubElement(root, "testcase", classname="x.NonGatedTest", name="mustPass")
        ET.ElementTree(root).write(self.folder / "TEST-matrix.xml", encoding="utf-8")

    def test_expected_four_gates_are_recorded_not_passing(self):
        self.report()
        result = verify(self.folder)
        self.assertEqual(("PASS", 46, 4, 50),
                         (result["status"], result["passed"], len(result["expected_variant_skips"]), result["cases"]))

    def test_missing_result_dir_fails(self):
        with self.assertRaises(ValueError):
            verify(self.folder / "missing")

    def test_empty_result_dir_fails(self):
        with self.assertRaises(ValueError):
            verify(self.folder)

    def test_shrunken_suite_cannot_claim_full_emulator_pass(self):
        self.report()
        tree = ET.parse(self.folder / "TEST-matrix.xml")
        root = tree.getroot()
        for item in list(root.findall("testcase[@classname='x.NormalRegression']"))[:10]:
            root.remove(item)
        tree.write(self.folder / "TEST-matrix.xml", encoding="utf-8")
        self.assertIn({"test": "debug-connected-suite", "kind": "suite-shrunk-below-50"}, verify(self.folder)["unexpected"])

    def test_gated_test_unexpectedly_executes_fails(self):
        self.report(gate="pass")
        self.assertEqual(4, len(verify(self.folder)["unexpected"]))

    def test_missing_gated_test_fails(self):
        self.report(missing=sorted(DEBUG_VARIANT_SKIPS)[0])
        self.assertEqual("FAIL", verify(self.folder)["status"])

    def test_unexpected_assertion_failure_is_not_whitelisted(self):
        self.report(other="failure")
        self.assertEqual([{"test": "x.NonGatedTest.mustPass", "kind": "failure"}], verify(self.folder)["unexpected"])

    def test_unexpected_error_is_not_whitelisted(self):
        self.report(other="error")
        self.assertEqual("FAIL", verify(self.folder)["status"])

    def test_unexpected_skip_is_not_whitelisted(self):
        self.report(other="skipped")
        self.assertEqual("FAIL", verify(self.folder)["status"])

    def test_assumption_in_unrelated_test_is_not_whitelisted(self):
        self.report()
        tree = ET.parse(self.folder / "TEST-matrix.xml")
        child = tree.getroot().find("testcase[@classname='x.NonGatedTest']")
        outcome = ET.SubElement(child, "failure")
        outcome.text = ASSUME
        tree.write(self.folder / "TEST-matrix.xml", encoding="utf-8")
        self.assertEqual("FAIL", verify(self.folder)["status"])

    def test_gated_unexpected_error_is_not_whitelisted(self):
        self.report(gate="error")
        self.assertEqual("FAIL", verify(self.folder)["status"])

    def test_corrupted_xml_fails(self):
        (self.folder / "TEST-broken.xml").write_text("<not-closed")
        with self.assertRaises(ET.ParseError):
            verify(self.folder)

    def test_duplicate_test_identity_fails(self):
        self.report(duplicate=True)
        with self.assertRaises(ValueError):
            verify(self.folder)


if __name__ == "__main__":
    unittest.main()
