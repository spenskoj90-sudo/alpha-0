#!/usr/bin/env python3
"""Fail closed before physical-test signing when an installed app uses another signer.

This validates Owner-supplied public certificate metadata, not a device attestation
or proof that a private signing key is in custody. Android still checks APK signatures.
"""
from __future__ import annotations

import argparse
import re
import sys

SHA256 = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^(0|[1-9][0-9]{0,9})$")
MAX_VERSION_CODE = 2_100_000_000


def verify(previous_version: str, installed_signer: str, expected_signer: str, new_identity_approved: str) -> str:
    if not VERSION.fullmatch(previous_version) or int(previous_version) > MAX_VERSION_CODE:
        raise ValueError("INVALID_PREVIOUS_VERSION_CODE")
    if not SHA256.fullmatch(expected_signer):
        raise ValueError("INVALID_PINNED_SIGNER")
    if new_identity_approved not in {"true", "false"}:
        raise ValueError("INVALID_NEW_IDENTITY_APPROVAL")

    baseline = int(previous_version)
    if baseline == 0:
        if installed_signer != "none" or new_identity_approved != "true":
            raise ValueError("NEW_IDENTITY_REQUIRES_EXPLICIT_OWNER_APPROVAL_AND_NO_INSTALLED_PACKAGE")
        return "NEW_IDENTITY_OWNER_APPROVED_NOT_AN_UPDATE"

    if not SHA256.fullmatch(installed_signer):
        raise ValueError("INSTALLED_CERTIFICATE_EVIDENCE_REQUIRED")
    if new_identity_approved != "false":
        raise ValueError("CANNOT_MIX_NEW_IDENTITY_AND_EXISTING_INSTALL")
    if installed_signer != expected_signer:
        raise ValueError("INSTALLED_SIGNER_MISMATCH")
    return "MATCHING_OWNER_SUPPLIED_CERTIFICATES_DEVICE_VERIFICATION_STILL_REQUIRED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-version-code", required=True)
    parser.add_argument("--installed-signer-sha256", required=True)
    parser.add_argument("--expected-signer-sha256", required=True)
    parser.add_argument("--new-identity-approved", required=True)
    args = parser.parse_args()
    try:
        outcome = verify(args.previous_version_code, args.installed_signer_sha256,
                         args.expected_signer_sha256, args.new_identity_approved)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
