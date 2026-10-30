#!/usr/bin/env python3
"""Offline static safety contract for a proposed SENTINEL Backblaze B2 target.

No network, account access, credentials, writes, or provider-side verification.
Success means only that supplied *strings* satisfy a fail-closed EU format.
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import urlsplit

REGION = re.compile(r"eu-central-[0-9]{3}\Z", re.ASCII)
BUCKET = re.compile(r"[a-z0-9](?:[a-z0-9-]{4,61})[a-z0-9]\Z", re.ASCII)


def validate_target(endpoint: str, region: str, bucket: str, max_ciphertext_bytes: int) -> None:
    """Reject unsafe or ambiguous configuration; never infer live B2 suitability."""
    if not REGION.fullmatch(region):
        raise ValueError("expected an explicitly configured B2 EU Central region")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid B2 endpoint") from exc
    # Exact URL comparison excludes user-info, ports, paths, queries, fragments,
    # non-HTTPS schemes, suffix attacks, aliases and non-EU endpoints.
    if port is not None or endpoint != f"https://s3.{region}.backblazeb2.com":
        raise ValueError("B2 endpoint must match the independently verified EU account region")
    if not BUCKET.fullmatch(bucket) or "--" in bucket:
        raise ValueError("invalid B2 bucket name (DNS-safe letters, numbers and hyphens only)")
    if type(max_ciphertext_bytes) is not int or max_ciphertext_bytes <= 0:
        raise ValueError("explicit positive pre-upload ciphertext byte cap required")


def require_version_id(value: str) -> None:
    """Refuse missing/invalid identity, without assuming B2's version-ID format."""
    if not value or value in {"None", "null", "-"} or len(value) > 512:
        raise ValueError("missing B2 object version ID")
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError("invalid B2 object version ID")


def main() -> int:
    p = argparse.ArgumentParser(description="Static-only Backblaze EU target validation; NOT live account verification")
    p.add_argument("--endpoint", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--bucket", required=True)
    p.add_argument("--max-ciphertext-bytes", type=int, required=True)
    a = p.parse_args()
    try:
        validate_target(a.endpoint, a.region, a.bucket, a.max_ciphertext_bytes)
    except ValueError as exc:
        p.error(str(exc))
    print("STATIC_B2_CONTRACT_PASS; account/billing/ACL/restore remain NOT_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
