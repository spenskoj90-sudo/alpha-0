#!/usr/bin/env python3
"""Read public apksigner certificate hashes; cryptographic verification is caller-owned."""
import argparse
import re
import sys

MARKER = re.compile(
    r"^(?:V[1-4] Signer(?: #\d+)?:|Signer #\d+) certificate SHA-(256|1) digest: ([0-9a-fA-F]+)$"
)

def certificate_digests(report: str) -> dict[str, str]:
    if not report or len(report) > 32768:
        raise ValueError("INVALID_REPORT")
    found = {"256": set(), "1": set()}
    for raw in report.splitlines():
        line = raw.strip()
        match = MARKER.fullmatch(line)
        if match:
            algo, value = match.groups()
            if len(value) != (64 if algo == "256" else 40):
                raise ValueError("MALFORMED_SIGNER")
            found[algo].add(value.lower())
        elif "certificate SHA-" in line and "digest:" in line:
            raise ValueError("UNRECOGNIZED_SIGNER")
    if len(found["256"]) != 1 or len(found["1"]) > 1:
        raise ValueError("MISSING_OR_MULTIPLE_SIGNERS")
    return {
        "sha256": next(iter(found["256"])),
        "sha1": next(iter(found["1"])) if found["1"] else "",
    }

if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--algorithm", required=True, choices=("sha256", "sha1"))
    cli.add_argument("--report", default="-")
    args = cli.parse_args()
    try:
        if args.report == "-":
            content = sys.stdin.read(32769)
        else:
            with open(args.report, encoding="utf-8") as f:
                content = f.read(32769)
        result = certificate_digests(content)[args.algorithm]
        if not result:
            raise ValueError("DIGEST_MISSING")
        print(result)
    except (OSError, ValueError, UnicodeError) as error:
        print(f"APK_SIGNER_BLOCKED: {error}", file=sys.stderr)
        sys.exit(2)
