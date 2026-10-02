#!/usr/bin/env python3
"""Allocate a stable-test APK code above the Owner-confirmed distributed baseline.

Workflow run numbers are scoped to each workflow, so the routine APK counter
cannot establish an update workflow's version. This does not prove installed
signer compatibility or authorize signing/custody changes.
"""
from __future__ import annotations

import argparse
import re
import sys
import time

MAX_VERSION_CODE = 2_100_000_000
DECIMAL = re.compile(r"^(?:0|[1-9][0-9]{0,9})$")


def allocate(previous: str, epoch: str) -> int:
    if not DECIMAL.fullmatch(previous) or not DECIMAL.fullmatch(epoch):
        raise ValueError("version baseline and epoch must be canonical non-negative decimal integers")
    baseline, timestamp = int(previous), int(epoch)
    value = max(baseline + 1, timestamp)
    if timestamp < 1 or value > MAX_VERSION_CODE:
        raise ValueError("physical-test versionCode would exceed the Android distribution range")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-version-code", required=True)
    parser.add_argument("--epoch-seconds", default=str(int(time.time())))
    args = parser.parse_args()
    try:
        value = allocate(args.previous_version_code, args.epoch_seconds)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
