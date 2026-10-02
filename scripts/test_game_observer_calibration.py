import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from game_observer_calibration import summarize


def sample():
    return {"schema": "sentinel.observer-calibration-input.v1", "sourceSha": "a" * 40,
        "apkSha256": "b" * 64, "signerSha256": "c" * 64, "package": "com.alpha0.app.physicaltest", "versionCode": 100000525,
        "game": {"package": "com.shatteredpixel.shatteredpixeldungeon", "versionName": "4.0.0", "versionCode": 912, "language": "en", "hud": "portrait-upper-left"},
        "environment": {"device": "Infinix X6731B", "api": 34}, "sampleKind": "synthetic",
        "samples": [{"sequence": 1, "ageMs": 100, "observed": {"current": 5, "maximum": 10}, "groundTruth": {"current": 5, "maximum": 10}}]}


class CalibrationTests(unittest.TestCase):
    def test_agreement_is_not_physical_or_source_acceptance(self):
        report = summarize(sample())
        self.assertEqual(report["exactMatches"], 1)
        self.assertEqual(report["sampleAgreement"], 1.0)
        self.assertEqual(report["status"], "PENDING_PHYSICAL_REVIEW")
        self.assertEqual(report["sourceTrust"], "UNVERIFIED")
        self.assertFalse(report["capabilityAvailable"])

    def test_error_missing_and_stale_samples_remain_in_denominator(self):
        value = sample()
        value["samples"] += [
            {"sequence": 2, "ageMs": 100, "observed": {"current": 3, "maximum": 12}, "groundTruth": {"current": 5, "maximum": 10}},
            {"sequence": 3, "ageMs": 100, "observed": None, "groundTruth": {"current": 5, "maximum": 10}},
            {"sequence": 4, "ageMs": 5001, "observed": {"current": 5, "maximum": 10}, "groundTruth": {"current": 5, "maximum": 10}}]
        report = summarize(value)
        self.assertEqual(report["sampleAgreement"], 0.25)
        self.assertEqual((report["missing"], report["stale"], report["mismatches"]), (1, 1, 1))
        self.assertEqual(report["maximumAbsoluteError"], {"current": 2, "maximum": 2})

    def test_rejects_raw_payloads_wrong_types_order_and_unbounded_samples(self):
        for mutate in [lambda v: v.update(frame="raw-pixels"), lambda v: v["game"].update(ocr="raw-text"),
                       lambda v: v.update(versionCode=True), lambda v: v["samples"][0]["observed"].update(current=-1),
                       lambda v: v["samples"].append(copy.deepcopy(v["samples"][0])), lambda v: v.update(samples=[]),
                       lambda v: v.update(samples=[copy.deepcopy(v["samples"][0])] * 33),
                       lambda v: v.update(sourceSha="short"), lambda v: v["environment"].update(api=33)]:
            value = sample()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize(value)

    def test_physical_label_alone_never_promotes_or_calibrates(self):
        value = sample()
        value["sampleKind"] = "physical-opt-in"
        report = summarize(value)
        self.assertEqual(report["status"], "PENDING_PHYSICAL_REVIEW")
        self.assertFalse(report["capabilityAvailable"])

    def test_cli_preserves_binding_and_rejects_ambiguous_or_oversized_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            source, output = path / "input.json", path / "output.json"
            command = [sys.executable, str(Path(__file__).with_name("game_observer_calibration.py")),
                       "--input", str(source), "--output", str(output)]
            source.write_text(json.dumps(sample()))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["apkSha256"], "b" * 64)
            output.unlink()
            for raw in ['{"schema":"old","schema":"new"}', " " * 32769]:
                source.write_text(raw)
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout.strip(), "CALIBRATION_INPUT_INVALID")
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
