#!/usr/bin/env python3
"""Fail closed if a signed release candidate would not upgrade its predecessor.

No signing secret is needed. Owner-reported baseline still requires independent
distribution evidence and an actual Android upgrade-over-install test.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

MAX_VERSION_CODE = 2_100_000_000
DECIMAL = re.compile(r"^(?:0|[1-9][0-9]{0,9})$")
VERSION_ASSIGNMENT = re.compile(r"^val canonicalVersionCode = ([1-9][0-9]*)$", re.MULTILINE)
PACKAGE_BADGING = re.compile(r"^package: name='([^']+)' versionCode='([^']+)'", re.MULTILINE)
EXPECTED_APP_ID = "com.alpha0.app"


def verify(gradle_source: str, previous_version: str, first_release_approved: str,
           badging: str | None = None) -> int:
    if not DECIMAL.fullmatch(previous_version):
        raise ValueError("INVALID_PREVIOUS_RELEASE_VERSION")
    if first_release_approved not in {"true", "false"}:
        raise ValueError("INVALID_FIRST_RELEASE_APPROVAL")
    matches = VERSION_ASSIGNMENT.findall(gradle_source)
    if len(matches) != 1:
        raise ValueError("AMBIGUOUS_RELEASE_VERSION_CODE")
    version = int(matches[0])
    previous = int(previous_version)
    if version > MAX_VERSION_CODE or previous > MAX_VERSION_CODE or version <= previous:
        raise ValueError("RELEASE_VERSION_NOT_HIGHER")
    if 'applicationId = "com.alpha0.app"' not in gradle_source:
        raise ValueError("RELEASE_APPLICATION_ID_CHANGED")
    if previous == 0 and first_release_approved != "true":
        raise ValueError("FIRST_RELEASE_LINEAGE_REQUIRES_OWNER_APPROVAL")
    if previous != 0 and first_release_approved != "false":
        raise ValueError("EXISTING_RELEASE_LINEAGE_CANNOT_BE_RESET")
    if badging is not None:
        found = PACKAGE_BADGING.findall(badging)
        if len(found) != 1 or found[0] != (EXPECTED_APP_ID, str(version)):
            raise ValueError("SIGNED_RELEASE_APK_IDENTITY_MISMATCH")
    return version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-version-code", required=True)
    parser.add_argument("--first-release-approved", required=True)
    parser.add_argument("--gradle-source", type=Path, default=Path("app/build.gradle.kts"))
    parser.add_argument("--badging-report", type=Path)
    args = parser.parse_args()
    try:
        source = args.gradle_source.read_text(encoding="utf-8")
        badging = args.badging_report.read_text(encoding="utf-8") if args.badging_report else None
        value = verify(source, args.previous_version_code, args.first_release_approved, badging)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
