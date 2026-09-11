from __future__ import annotations

import hashlib
import re

_FINGERPRINT_RE = re.compile(r"^[0-9A-Fa-f]{64}$")


def normalize_sha256_fingerprint(value: str) -> str:
    """Normalize a SHA-256 certificate fingerprint to uppercase hex."""
    compact = value.replace(":", "").replace(" ", "")
    if not _FINGERPRINT_RE.fullmatch(compact):
        raise ValueError("TLS peer SHA-256 fingerprint must contain exactly 64 hexadecimal characters")
    return compact.upper()


def certificate_sha256_fingerprint(certificate_der: bytes) -> str:
    """Return the SHA-256 fingerprint of a DER-encoded peer certificate."""
    if not certificate_der:
        raise ValueError("TLS peer certificate is empty")
    return hashlib.sha256(certificate_der).hexdigest().upper()


def verify_certificate_fingerprint(certificate_der: bytes, expected: str) -> str:
    """Fail closed unless the peer certificate matches the configured pin."""
    expected_normalized = normalize_sha256_fingerprint(expected)
    actual = certificate_sha256_fingerprint(certificate_der)
    if actual != expected_normalized:
        raise PermissionError("TLS_PEER_CERTIFICATE_FINGERPRINT_MISMATCH")
    return actual
