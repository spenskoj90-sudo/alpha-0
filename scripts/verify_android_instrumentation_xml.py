#!/usr/bin/env python3
"""Fail-closed JUnit XML accounting for debug Android emulator instrumentation.

Four physicalTest-only tests use JUnit Assume on a debug target. Android Gradle
serializes these into <failure> nodes, even though the runner exits successfully.
These exact fixture gates are recorded as EXPECTED_VARIANT_SKIP, never PASS.
All other reported failures, errors and skips block the workflow.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# These four cases are exclusively exercised by android-update-e2e physicalTest.
DEBUG_VARIANT_SKIPS = frozenset({
    ("com.alpha0.app.security.UpgradeContinuityInstrumentedTest", "seedDeviceState"),
    ("com.alpha0.app.security.UpgradeContinuityInstrumentedTest", "verifyPreservedDeviceState"),
    ("com.alpha0.app.update.UpdatePreflightInstrumentedTest", "acceptsCompatibleNewerSameSignerApk"),
    ("com.alpha0.app.update.UpdatePreflightInstrumentedTest", "rejectsSameVersionAfterUpgrade"),
})


def verify(root: Path) -> dict:
    if not root.is_dir():
        raise ValueError("Android connected-test results directory is missing")
    xml_files = sorted(root.glob("**/TEST-*.xml"))
    if not xml_files:
        raise ValueError("No connected Android TEST XML reports: cannot claim emulator PASS")

    tests = {}
    failures = []
    expected_skips = []
    for path in xml_files:
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Unbounded Android test XML report")
        xml = ET.parse(path).getroot()
        if xml.tag not in ("testsuite", "testsuites"):
            raise ValueError("Unexpected Android test report root")
        cases = list(xml.iter("testcase"))
        if not cases:
            raise ValueError("Empty Android test suite")
        # Android's own suite summary must reconcile with its testcase records.
        # Otherwise a green set of cases could conceal an unmatched suite error
        # or a truncated report. Fail rather than re-labeling missing evidence.
        leaf_suites = [element for element in xml.iter("testsuite")
                       if not any(child.tag == "testsuite" for child in element)]
        if not leaf_suites:
            raise ValueError("Android test suite summary missing")
        for suite in leaf_suites:
            scoped = list(suite.iter("testcase"))
            actual = {"tests": len(scoped),
                      "failures": sum(c.find("failure") is not None for c in scoped),
                      "errors": sum(c.find("error") is not None for c in scoped),
                      "skipped": sum(c.find("skipped") is not None for c in scoped)}
            for key, amount in actual.items():
                try:
                    reported = int(suite.attrib[key])
                except (KeyError, ValueError):
                    raise ValueError("Missing/invalid Android suite counter: " + key)
                if amount != reported:
                    raise ValueError("Inconsistent Android suite counter: " + key)
        for case in cases:
            key = (case.attrib.get("classname"), case.attrib.get("name"))
            if not all(key) or key in tests:
                raise ValueError("Missing or repeated Android test identity: " + repr(key))
            children = [x for x in case if x.tag in ("failure", "error", "skipped")]
            if len(children) > 1:
                failures.append({"test": ".".join(key), "kind": "multiple-outcomes"})
                continue
            if children:
                child = children[0]
                reason = (child.text or "") + "\n" + child.attrib.get("message", "")
                # Exact exemption only when the Android runner serialized the
                # diagnostic-only Assume guard as a JUnit <failure> node.
                allowed = (key in DEBUG_VARIANT_SKIPS and child.tag == "failure"
                           and "org.junit.AssumptionViolatedException" in reason
                           and "org.junit.Assume.assumeTrue" in reason
                           and "got: <false>, expected: is <true>" in reason)
                if allowed:
                    expected_skips.append(".".join(key))
                    tests[key] = "EXPECTED_VARIANT_SKIP"
                else:
                    failures.append({"test": ".".join(key), "kind": child.tag})
                    tests[key] = "FAIL"
            else:
                if key in DEBUG_VARIANT_SKIPS:
                    failures.append({"test": ".".join(key), "kind": "expected-variant-skip-not-triggered"})
                tests[key] = "PASS"
    # The reviewed full debug regression at exact source 1502d74d on API34/36
    # contained 50 cases, of which four were variant-gated. Detect accidentally
    # filtered or materially narrowed emulator suites instead of claiming PASS.
    if len(tests) < 50:
        failures.append({"test": "debug-connected-suite", "kind": "suite-shrunk-below-50"})
    missing = sorted(".".join(k) for k in DEBUG_VARIANT_SKIPS - tests.keys())
    if missing:
        failures.extend({"test": k, "kind": "missing-variant-gated-test"} for k in missing)
    result = {
        "status": "PASS" if not failures else "FAIL",
        "reports": len(xml_files),
        "cases": len(tests),
        "passed": sum(x == "PASS" for x in tests.values()),
        "expected_variant_skips": sorted(expected_skips),
        "unexpected": failures,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path,
                        default=Path("app/build/outputs/androidTest-results/connected/debug"))
    args = parser.parse_args()
    try:
        result = verify(args.results_dir)
    except (ValueError, OSError, ET.ParseError) as error:
        print(json.dumps({"status": "FAIL", "reason": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
