from __future__ import annotations

import hashlib
import secrets
import time
from enum import Enum
from threading import Lock


class IntegrityTier(str, Enum):
    STRONG = "MEETS_STRONG_INTEGRITY"
    DEVICE = "MEETS_DEVICE_INTEGRITY"
    BASIC = "MEETS_BASIC_INTEGRITY"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


CRITICAL_ACTIONS = frozenset(
    {
        "device:rotate",
        "device:revoke",
        "event:write",
        "admin:entitlement:create",
        "knowledge:recommend",
    }
)

BASIC_ACTIONS = frozenset({"character:read", "game:read", "audit:read"})


def classify_verdicts(verdicts: set[str] | frozenset[str]) -> IntegrityTier:
    if "MEETS_STRONG_INTEGRITY" in verdicts:
        return IntegrityTier.STRONG
    if "MEETS_DEVICE_INTEGRITY" in verdicts:
        return IntegrityTier.DEVICE
    if "MEETS_BASIC_INTEGRITY" in verdicts:
        return IntegrityTier.BASIC
    if not verdicts:
        return IntegrityTier.UNKNOWN
    return IntegrityTier.FAILED


def authorize_for_tier(tier: IntegrityTier, action: str) -> bool:
    if tier is IntegrityTier.STRONG:
        return True
    if tier is IntegrityTier.DEVICE:
        return action not in CRITICAL_ACTIONS
    if tier is IntegrityTier.BASIC:
        return action in BASIC_ACTIONS
    return False


class IntegrityNonceStore:
    """Server-issued attestation nonces with one-time consume and TTL."""

    def __init__(self, ttl_seconds: int = 120) -> None:
        self.ttl_seconds = ttl_seconds
        self._nonces: dict[str, dict[str, float | bool]] = {}
        self._lock = Lock()

    def issue(self) -> str:
        nonce = secrets.token_urlsafe(32)
        digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        with self._lock:
            self._nonces[digest] = {"expires_at": time.time() + self.ttl_seconds, "used": False}
        return nonce

    def consume(self, nonce: str) -> bool:
        if not nonce:
            return False
        digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        with self._lock:
            record = self._nonces.get(digest)
            if not record or record["used"] or float(record["expires_at"]) <= time.time():
                return False
            record["used"] = True
            return True
