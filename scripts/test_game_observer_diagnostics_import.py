"""Regression suite for privacy-bounded Android numeric calibration export import."""
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

from game_observer_diagnostics_import import extracted_report, read_events, verify_export_identity

CAMPAIGN = "01234567-89ab-4def-8234-1234567890ab"
OTHER = "10234567-89ab-4def-8234-1234567890ab"
CAPTURE = "21234567-89ab-4def-8234-1234567890ab"
OTHER_CAPTURE = "31234567-89ab-4def-8234-1234567890ab"
ARGS = dict(campaign=None, source_sha="a" * 40, apk_sha256="b" * 64,
            signer_sha256="c" * 64, apk_version_code=100000641,
            game_signer_sha256="d" * 64, language="en",
            hud="portrait-upper-left", device="Infinix X6731B", api=34)


def event(seq=1, campaign=CAMPAIGN, **changes):
    age = changes.pop("age_ms", 200)
    frame_at = 100000 + seq * 10000
    details = dict(
        calibration_campaign=campaign, sample_sequence=seq,
        capture_id=CAPTURE, capture_frame_sequence=seq,
        frame_captured_at_ms=frame_at, sample_saved_at_ms=frame_at + age,
        game_package="com.shatteredpixel.shatteredpixeldungeon",
        game_version="4.0.0", game_version_code=912,
        game_signer_sha256="d" * 64, age_ms=age,
        recognized_current=8, recognized_maximum=10,
        ground_truth_current=8, ground_truth_maximum=10,
        source_status="UNVERIFIED", sample_kind="user-opt-in",
        device_environment="UNVERIFIED",
        diagnostic_note="never copy this unrelated free-text field",
    )
    details.update(changes)
    return dict(component="GAME", event="CALIBRATION_NUMERIC_SAMPLE",
                result="OBSERVED", details=details,
                exception_stack="never copy arbitrary stack trace")


def report(events, **changes):
    return extracted_report(events, **(ARGS | changes))


class OptInDiagnosticsImportTests(unittest.TestCase):
    def test_only_numeric_opt_in_fields_are_retained_and_never_promote(self):
        value = report([event(), event(2, age_ms=6500),
                        event(3, recognized_current=None, recognized_maximum=None)])
        self.assertEqual(value["schema"], "sentinel.observer-calibration-summary.v2")
        self.assertEqual(value["game"]["signerSha256"], "d" * 64)
        self.assertEqual(value["sampleKind"], "physical-opt-in")
        self.assertEqual(value["samples"], 3)
        self.assertEqual(value["exactMatches"], 1)
        self.assertEqual(value["stale"], 1)
        self.assertEqual(value["missing"], 1)
        self.assertEqual(value["status"], "PENDING_PHYSICAL_REVIEW")
        self.assertEqual(value["sourceTrust"], "UNVERIFIED")
        self.assertEqual(value["recognizerConfidence"], "UNCALIBRATED")
        self.assertFalse(value["capabilityAvailable"])
        self.assertEqual(len(value["frameTraceDigestSha256"]), 64)
        for forbidden in ("diagnostic_note", "exception_stack", "never copy",
                          CAPTURE, "capture_id", "frame_captured_at_ms", "sample_saved_at_ms"):
            self.assertNotIn(forbidden, json.dumps(value))

    def test_corrupted_or_inconsistent_campaigns_are_denied(self):
        modifications = [
            [event(2)],                              # Missing first observation
            [event(), event(1)],                     # Duplicate sequence
            [event(), event(3)],                     # Gap
            [event(), event(2, game_version="4.0.1")],
            [event(), event(2, game_signer_sha256="e" * 64)],
            [event(game_signer_sha256=None)],
            [event(game_signer_sha256="not-hex")],
            [event(source_status="VERIFIED")],
            [event(sample_kind="automatic")],
            [event(device_environment="ATTESTED")],
            [event(recognized_current=8, recognized_maximum=None)],
            [event(ground_truth_current=True)],
            [event(capture_id=None)],
            [event(capture_id="NOT_A_UUID")],
            [event(), event(2, capture_id=OTHER_CAPTURE)],
            [event(), event(2, capture_frame_sequence=1)],
            [event(), event(2, capture_frame_sequence=0)],
            [event(capture_frame_sequence=True)],
            [event(frame_captured_at_ms=True)],
            [event(sample_saved_at_ms=True)],
            [event(frame_captured_at_ms=-1, sample_saved_at_ms=199, age_ms=200)],
            [event(frame_captured_at_ms=2**63)],
            [event(sample_saved_at_ms=2**63)],
            [event(age_ms=300001)],
            [event(sample_saved_at_ms=109999)],
            [event(sample_saved_at_ms=110201)],
            [event(), event(2, frame_captured_at_ms=109999)],
            [event(age_ms=250000), event(2)],  # saved timestamps regress
            [event(2, OTHER)],                       # Mixed campaigns ambiguous
            [event()] * 33,
        ]
        for rows in modifications:
            with self.subTest(rows=len(rows), last=rows[-1]["details"]), self.assertRaises((ValueError, TypeError)):
                report(rows)


    def test_new_ocr_completion_timing_is_checked_without_relabelling_save_age(self):
        first = event(ocr_completed_at_ms=110050, ocr_processing_latency_ms=50,
                      age_ms=6200)
        # The constructed event must keep acquisition, Save and age consistent.
        first["details"]["sample_saved_at_ms"] = 116200
        fresh = report([first])
        assert fresh["stale"] == 1
        assert fresh["exactMatches"] == 0
        assert fresh["sourceTrust"] == "UNVERIFIED"
        assert fresh["capabilityAvailable"] is False
        legacy = copy.deepcopy(first)
        legacy["details"].pop("ocr_completed_at_ms")
        legacy["details"].pop("ocr_processing_latency_ms")
        assert report([legacy])["samples"] == 1
        assert fresh["frameTraceDigestSha256"] != report([legacy])["frameTraceDigestSha256"]
        for key, value in [
            ("ocr_completed_at_ms", None),
            ("ocr_completed_at_ms", 109999),
            ("ocr_completed_at_ms", 116201),
            ("ocr_processing_latency_ms", True),
            ("ocr_processing_latency_ms", 51),
            ("ocr_processing_latency_ms", 5001),
        ]:
            malformed = copy.deepcopy(first)
            malformed["details"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises((ValueError, TypeError)):
                report([malformed])
        malformed = copy.deepcopy(first)
        malformed["details"].pop("ocr_completed_at_ms")
        with self.assertRaises(ValueError):
            report([malformed])

    def test_frame_trace_hash_changes_without_disclosing_raw_capture_identity(self):
        first = report([event(), event(2)])
        second = report([event(), event(2, capture_frame_sequence=3)])
        self.assertNotEqual(first["frameTraceDigestSha256"], second["frameTraceDigestSha256"])
        self.assertEqual(first["sampleAgreement"], second["sampleAgreement"])
        self.assertEqual(first["inputDigest"], second["inputDigest"])
        self.assertNotIn(CAPTURE, json.dumps(first))
        self.assertNotIn("frame_captured_at_ms", json.dumps(first))
        self.assertFalse(first["capabilityAvailable"])

    def test_legacy_export_without_frame_provenance_fails_closed(self):
        older = event()
        for key in ("capture_id", "capture_frame_sequence",
                    "frame_captured_at_ms", "sample_saved_at_ms"):
            older["details"].pop(key)
        with self.assertRaises((ValueError, TypeError)):
            report([older])

    def test_two_campaigns_require_explicit_selection(self):
        rows = [event(), event(1, OTHER), event(2, OTHER)]
        with self.assertRaises(ValueError):
            report(rows)
        chosen = report(rows, campaign=OTHER)
        self.assertEqual(chosen["samples"], 2)
        with self.assertRaises(ValueError):
            report(rows, campaign="2026-10-14")

    def test_game_signer_claim_must_match_all_exported_samples(self):
        with self.assertRaises(ValueError):
            report([event()], game_signer_sha256="f" * 64)
        with self.assertRaises(ValueError):
            report([event()], signer_sha256="NOT_A_DIGEST")
        with self.assertRaises(ValueError):
            report([event()], api=33)
        with self.assertRaises(ValueError):
            report([event()], language="unknown")

    def test_export_identity_must_match_exact_apk_and_new_phone(self):
        start = dict(source_sha="a" * 40, package_name="com.alpha0.app.physicaltest",
                     version_code=100000641, build_type="physicalTest",
                     diagnostics_mode="FORENSIC_TEST", runtime_environment="staging",
                     sdk=35, manufacturer="Xiaomi", model="25028PC03G")
        signer = dict(package_name="com.alpha0.app.physicaltest",
                      installed_version_code=100000641, signer_count=1,
                      multiple_signers=False, identity_evidence="PACKAGE_MANAGER",
                      signer_cert_sha256="c" * 64)
        kwargs = dict(source_sha="a" * 40, signer_sha256="c" * 64,
                      apk_version_code=100000641, device="Xiaomi 25028PC03G", api=35)
        verify_export_identity(start, signer, **kwargs)
        for change in ({"sdk": 34}, {"source_sha": "b" * 40},
                       {"model": "other"}, {"build_type": "release"}):
            with self.assertRaises(ValueError):
                verify_export_identity(start | change, signer, **kwargs)
        for change in ({"signer_count": 2}, {"signer_cert_sha256": "d" * 64},
                       {"multiple_signers": True}):
            with self.assertRaises(ValueError):
                verify_export_identity(start, signer | change, **kwargs)
        with self.assertRaises(ValueError):
            verify_export_identity(None, signer, **kwargs)

    def test_gzip_bounds_utf8_json_duplicates_and_unrelated_logs(self):
        with tempfile.TemporaryDirectory() as work:
            archive = Path(work) / "diagnostics.jsonl.gz"
            root = [dict(component="AUTH", event="LOGIN",
                         details={"access_token": "never include"}),
                    event()]
            archive.write_bytes(gzip.compress(("\n".join(json.dumps(x) for x in root) + "\n").encode()))
            loaded = read_events(archive)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(report(loaded)["samples"], 1)

            for raw in [b'{"component":"GAME","component":"GAME"}\n',
                        b'not json\n',
                        b'{"component":"GAME"}' + b' ' * (65537) + b'\n',
                        b'X' * (2 * 1024 * 1024 + 1)]:
                archive.write_bytes(gzip.compress(raw))
                with self.subTest(size=len(raw)), self.assertRaises((ValueError, UnicodeError)):
                    read_events(archive)

            archive.write_bytes(gzip.compress(b'{"component":"AUTH","event":"LOGIN"}\n'))
            with self.assertRaises(ValueError):
                read_events(archive)

    def test_cli_output_is_non_overwriting_conservative_and_does_not_print_private_data(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            source, output = root / "diagnostics.gz", root / "summary.json"
            start = {"component": "RUNTIME", "event": "PROCESS_START", "result": "SUCCESS",
                     "details": {"source_sha": "a" * 40, "package_name": "com.alpha0.app.physicaltest",
                                 "version_code": 100000641, "build_type": "physicalTest",
                                 "diagnostics_mode": "FORENSIC_TEST", "runtime_environment": "staging",
                                 "sdk": 34, "manufacturer": "Infinix", "model": "X6731B"}}
            signer = {"component": "RUNTIME", "event": "PACKAGE_SIGNER", "result": "OBSERVED",
                      "details": {"package_name": "com.alpha0.app.physicaltest",
                                  "installed_version_code": 100000641, "signer_count": 1,
                                  "multiple_signers": False, "identity_evidence": "PACKAGE_MANAGER",
                                  "signer_cert_sha256": "c" * 64}}
            source.write_bytes(gzip.compress(("\n".join(map(json.dumps, (start, signer, event()))) + "\n").encode()))
            command = [
                sys.executable, str(Path(__file__).with_name("game_observer_diagnostics_import.py")),
                "--diagnostics", str(source), "--output", str(output),
                "--source-sha", "a" * 40, "--apk-sha256", "b" * 64,
                "--signer-sha256", "c" * 64, "--apk-version-code", "100000641",
                "--game-signer-sha256", "d" * 64, "--language", "en",
                "--hud", "portrait-upper-left",
                "--device", "Infinix X6731B", "--api", "34",
            ]
            process = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("PENDING_PHYSICAL_REVIEW", process.stdout)
            self.assertNotIn("never copy", process.stdout)
            result = json.loads(output.read_text())
            self.assertEqual(result["exactMatches"], 1)
            self.assertFalse(result["capabilityAvailable"])
            existing = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 1)
            self.assertEqual(output.read_bytes(), existing)


if __name__ == "__main__":
    unittest.main()
