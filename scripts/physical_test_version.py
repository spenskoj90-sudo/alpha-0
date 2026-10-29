#!/usr/bin/env python3
"""Allocate installable physical-test versionCode without wall-clock exhaustion.

GitHub run number advances within this dedicated signed-update workflow.
The Owner's highest previously distributed versionCode is an additional floor.
Routine ephemeral CI has a separate non-installable counter.
"""
from __future__ import annotations

import argparse
import re
import sys

MAX_VERSION_CODE = 2_100_000_000
WORKFLOW_VERSION_BASE = 100_000_000
DECIMAL = re.compile(r"^(?:0|[1-9][0-9]{0,9})$")


def allocate(previous: str, workflow_run_number: str) -> int:
    if not DECIMAL.fullmatch(previous) or not DECIMAL.fullmatch(workflow_run_number):
        raise ValueError("baseline and workflow run number must be canonical non-negative decimal integers")
    baseline, run_number = int(previous), int(workflow_run_number)
    if run_number < 1 or baseline >= MAX_VERSION_CODE:
        raise ValueError("run number must be positive and baseline must leave versionCode headroom")
    value = max(baseline + 1, WORKFLOW_VERSION_BASE + run_number)
    if value > MAX_VERSION_CODE:
        raise ValueError("physical-test versionCode exceeds the Android distribution range")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-version-code", required=True)
    parser.add_argument("--workflow-run-number", required=True)
    args = parser.parse_args()
    try:
        value = allocate(args.previous_version_code, args.workflow_run_number)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
