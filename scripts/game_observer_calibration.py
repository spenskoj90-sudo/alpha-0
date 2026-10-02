#!/usr/bin/env python3
"""Summarize opt-in numeric HUD comparisons without pixels or raw OCR.

Input assertions are not device attestations. Every report remains pending
physical review and UNVERIFIED; this tool cannot grant a capability or action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def require(condition: bool) -> None:
    if not condition:
        raise ValueError("CALIBRATION_INPUT_INVALID")


def keys(value: object, expected: set[str]) -> None:
    require(type(value) is dict and set(value) == expected)


def integer(value: object, minimum: int, maximum: int) -> None:
    require(type(value) is int and minimum <= value <= maximum)


def health(value: object) -> None:
    keys(value, {"current", "maximum"})
    integer(value["maximum"], 1, 999999)
    integer(value["current"], 0, value["maximum"])


def summarize(value: dict) -> dict:
    keys(value, {"schema", "sourceSha", "apkSha256", "signerSha256", "package", "versionCode", "game", "environment", "sampleKind", "samples"})
    require(value["schema"] == "sentinel.observer-calibration-input.v1")
    for field, size in (("sourceSha", 40), ("apkSha256", 64), ("signerSha256", 64)):
        require(type(value[field]) is str and re.fullmatch(r"[0-9a-f]{" + str(size) + "}", value[field]) is not None)
    require(value["package"] == "com.alpha0.app.physicaltest")
    integer(value["versionCode"], 1, 2100000000)
    game = value["game"]
    keys(game, {"package", "versionName", "versionCode", "language", "hud"})
    require(game["package"] == "com.shatteredpixel.shatteredpixeldungeon")
    require(type(game["versionName"]) is str and re.fullmatch(r"[A-Za-z0-9._+-]{1,64}", game["versionName"]) is not None)
    integer(game["versionCode"], 1, 2100000000)
    require(game["language"] in ("ru", "en") and game["hud"] in ("portrait-upper-left", "landscape-upper-left"))
    keys(value["environment"], {"device", "api"})
    require(value["environment"]["device"] == "Infinix X6731B")
    integer(value["environment"]["api"], 34, 34)
    require(value["sampleKind"] in ("synthetic", "physical-opt-in"))
    rows = value["samples"]
    require(type(rows) is list and 1 <= len(rows) <= 32)
    matches = missing = stale = mismatches = 0
    errors = {"current": 0, "maximum": 0}
    previous = -1
    for row in rows:
        keys(row, {"sequence", "ageMs", "observed", "groundTruth"})
        integer(row["sequence"], previous + 1, 2100000000)
        previous = row["sequence"]
        integer(row["ageMs"], 0, 300000)
        health(row["groundTruth"])
        if row["observed"] is not None:
            health(row["observed"])
        if row["ageMs"] > 5000:
            stale += 1
        elif row["observed"] is None:
            missing += 1
        else:
            for field in errors:
                errors[field] = max(errors[field], abs(row["observed"][field] - row["groundTruth"][field]))
            if row["observed"] == row["groundTruth"]:
                matches += 1
            else:
                mismatches += 1
    n = len(rows)
    agreement = matches / n
    z2 = 1.96 ** 2
    # Sampling uncertainty only: not model confidence or an acceptance threshold.
    lower = (agreement + z2 / (2 * n) - 1.96 * math.sqrt(agreement * (1 - agreement) / n + z2 / (4 * n * n))) / (1 + z2 / n)
    binding = {key: value[key] for key in ("sourceSha", "apkSha256", "signerSha256", "package", "versionCode", "game", "environment", "sampleKind")}
    return {"schema": "sentinel.observer-calibration-summary.v1", **binding,
        "inputDigest": hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "status": "PENDING_PHYSICAL_REVIEW", "sourceTrust": "UNVERIFIED", "capabilityAvailable": False,
        "signal": "health_ratio", "samples": n, "exactMatches": matches, "missing": missing, "stale": stale,
        "mismatches": mismatches, "sampleAgreement": agreement, "sampleAgreement95LowerBound": max(0.0, lower),
        "maximumAbsoluteError": errors, "recognizerConfidence": "UNCALIBRATED"}


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        require(args.input.stat().st_size <= 32768)
        report = summarize(json.loads(args.input.read_text(), object_pairs_hook=unique_object))
    except (ValueError, TypeError, KeyError, OSError):
        print("CALIBRATION_INPUT_INVALID")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("CALIBRATION_SUMMARY=PENDING_PHYSICAL_REVIEW sourceTrust=UNVERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
