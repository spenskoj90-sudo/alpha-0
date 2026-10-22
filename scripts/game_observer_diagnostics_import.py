#!/usr/bin/env python3
"""Extract opt-in Android health comparisons from an Owner-shared diagnostic export.

Never trusts a MediaProjection app source, installed-package publisher, phone,
APK manifest, or signer assertion on its own. Produces only pending review evidence.
Never copies raw OCR, screenshots, arbitrary diagnostics or credentials.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import uuid

from game_observer_calibration import require, summarize, unique_object

MAX_UNCOMPRESSED = 2 * 1024 * 1024
MAX_LINES = 4000
MAX_LINE_BYTES = 64 * 1024
PACKAGE = "com.shatteredpixel.shatteredpixeldungeon"


def read_events(path: Path) -> list[dict]:
    require(path.suffix == ".gz")
    require(0 < path.stat().st_size <= MAX_UNCOMPRESSED)
    with gzip.open(path, "rb") as stream:
        raw = stream.read(MAX_UNCOMPRESSED + 1)
    require(0 < len(raw) <= MAX_UNCOMPRESSED)
    lines = raw.splitlines()
    require(1 <= len(lines) <= MAX_LINES)
    events = []
    for line in lines:
        require(0 < len(line) <= MAX_LINE_BYTES)
        parsed = json.loads(line.decode("utf-8"), object_pairs_hook=unique_object)
        require(type(parsed) is dict)
        if parsed.get("component") == "GAME" and parsed.get("event") == "CALIBRATION_NUMERIC_SAMPLE":
            require(parsed.get("result") == "OBSERVED")
            events.append(parsed)
    require(bool(events))
    return events


def field(details: dict, key: str, typ: type) -> object:
    require(key in details and type(details[key]) is typ)
    return details[key]


def extracted_report(
    events: list[dict], *,
    campaign: str | None,
    source_sha: str,
    apk_sha256: str,
    signer_sha256: str,
    apk_version_code: int,
    game_signer_sha256: str,
    language: str,
    hud: str,
    device: str,
    api: int,
) -> dict:
    # Campaign IDs are local UUIDs, not identity or capture attestations.
    groups: dict[str, list[dict]] = {}
    for event in events:
        details = event.get("details")
        require(type(details) is dict)
        campaign_id = field(details, "calibration_campaign", str)
        require(str(uuid.UUID(campaign_id)) == campaign_id)
        groups.setdefault(campaign_id, []).append(details)
    if campaign is None:
        require(len(groups) == 1)
        campaign = next(iter(groups))
    else:
        require(str(uuid.UUID(campaign)) == campaign and campaign in groups)

    samples = groups[campaign]
    require(1 <= len(samples) <= 32)
    game_version: str | None = None
    game_code: int | None = None
    capture_id: str | None = None
    last_frame_sequence = 0
    last_frame_at = -1
    last_saved_at = -1
    frame_trace = []
    rows = []
    for i, details in enumerate(samples, start=1):
        require(field(details, "sample_sequence", int) == i)
        # Bind each comparison to an actual capture generation and advancing
        # frame sequence. This is local diagnostic metadata, not attestation.
        observed_capture = field(details, "capture_id", str)
        require(str(uuid.UUID(observed_capture)) == observed_capture)
        if capture_id is None:
            capture_id = observed_capture
        require(observed_capture == capture_id)
        frame_sequence = field(details, "capture_frame_sequence", int)
        frame_at = field(details, "frame_captured_at_ms", int)
        saved_at = field(details, "sample_saved_at_ms", int)
        require(last_frame_sequence < frame_sequence <= 2**63 - 1)
        require(0 <= frame_at and last_frame_at <= frame_at <= saved_at <= 2**63 - 1)
        require(last_saved_at <= saved_at)
        age = field(details, "age_ms", int)
        require(0 <= age <= 300000 and saved_at - frame_at == age)
        last_frame_sequence = frame_sequence
        last_frame_at = frame_at
        last_saved_at = saved_at
        frame_trace.append([campaign, observed_capture, frame_sequence, frame_at, saved_at])
        require(field(details, "game_package", str) == PACKAGE)
        version = field(details, "game_version", str)
        code = field(details, "game_version_code", int)
        require(field(details, "game_signer_sha256", str) == game_signer_sha256)
        require(field(details, "source_status", str) == "UNVERIFIED")
        require(field(details, "sample_kind", str) == "user-opt-in")
        require(field(details, "device_environment", str) == "UNVERIFIED")
        if game_version is None:
            game_version, game_code = version, code
        require((version, code) == (game_version, game_code))
        gt = {"current": field(details, "ground_truth_current", int),
              "maximum": field(details, "ground_truth_maximum", int)}
        current = details.get("recognized_current")
        maximum = details.get("recognized_maximum")
        require((current is None and maximum is None) or
                (type(current) is int and type(maximum) is int))
        observed = None if current is None else {"current": current, "maximum": maximum}
        rows.append({"sequence": i, "ageMs": age,
                     "groundTruth": gt, "observed": observed})

    assert game_version is not None and game_code is not None
    input_data = {
        "schema": "sentinel.observer-calibration-input.v2",
        "sourceSha": source_sha, "apkSha256": apk_sha256,
        "signerSha256": signer_sha256,
        "package": "com.alpha0.app.physicaltest",
        "versionCode": apk_version_code,
        "game": {"package": PACKAGE, "versionName": game_version,
                 "versionCode": game_code, "signerSha256": game_signer_sha256,
                 "language": language, "hud": hud},
        "environment": {"device": device, "api": api},
        "sampleKind": "physical-opt-in",
        "samples": rows,
    }
    # Existing strict input validator includes missing/stale in denominator and
    # ALWAYS keeps capability unavailable, regardless of numeric agreement.
    report = summarize(input_data)
    # Hashed trace enables later reconciliation with the retained diagnostics
    # without leaking session UUIDs or monotonic timestamps into the summary.
    # This is diagnostic consistency evidence, NOT a trusted source signature.
    report["frameTraceDigestSha256"] = hashlib.sha256(
        json.dumps(frame_trace, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()
    return report


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--diagnostics", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--campaign", default=None, help="Required if export has more than one campaign")
    cli.add_argument("--source-sha", required=True, help="Asserted by external APK build manifest")
    cli.add_argument("--apk-sha256", required=True, help="Asserted APK file digest")
    cli.add_argument("--signer-sha256", required=True, help="Asserted SENTINEL APK signer digest")
    cli.add_argument("--apk-version-code", type=int, required=True)
    cli.add_argument("--game-signer-sha256", required=True, help="Compare with observed game diagnostic digest")
    cli.add_argument("--language", choices=("ru", "en"), required=True)
    cli.add_argument("--hud", choices=("portrait-upper-left", "landscape-upper-left"), required=True)
    cli.add_argument("--device", required=True, help="Exact manufacturer and model verified from the exported PROCESS_START and artifact evidence")
    cli.add_argument("--api", type=int, required=True, help="Observed Android API level; never infer from a previous device")
    args = cli.parse_args()
    try:
        report = extracted_report(
            read_events(args.diagnostics), campaign=args.campaign,
            source_sha=args.source_sha, apk_sha256=args.apk_sha256,
            signer_sha256=args.signer_sha256,
            apk_version_code=args.apk_version_code,
            game_signer_sha256=args.game_signer_sha256,
            language=args.language, hud=args.hud, device=args.device, api=args.api,
        )
        # Do not overwrite a prior accepted evidence output. All input paths
        # are explicitly supplied by the engineer, not read from private apps.
        with args.output.open("x", encoding="utf-8") as dest:
            json.dump(report, dest, sort_keys=True, indent=2)
            dest.write("\n")
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, EOFError, AssertionError):
        print("CALIBRATION_IMPORT_INVALID")
        return 1
    print("CALIBRATION_SUMMARY=PENDING_PHYSICAL_REVIEW sourceTrust=UNVERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
