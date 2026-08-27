from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any, Callable, Protocol


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


@dataclass(frozen=True)
class IntegrityVerificationResult:
    tier: IntegrityTier
    reason: str
    trusted: bool
    package_name: str | None = None
    certificate_digest: str | None = None
    device_recognition_verdict: tuple[str, ...] = ()


class TokenDecoder(Protocol):
    def __call__(self, integrity_token: str) -> dict[str, Any]: ...


def _normalize_digest(value: str) -> str:
    return value.replace(":", "").replace(" ", "").upper()


class PlayIntegrityVerifier:
    """Server-side Google Play Integrity token verification.

    Credentials are never embedded. Configuration:
      SENTINEL_PLAY_INTEGRITY_AUDIENCE — Google Cloud project number
      SENTINEL_PLAY_INTEGRITY_PACKAGE — expected applicationId
      SENTINEL_PLAY_INTEGRITY_CERT_DIGEST — expected signing cert SHA-256 (colon or plain hex)
      SENTINEL_PLAY_INTEGRITY_ACCESS_TOKEN — optional OAuth access token for decode API
        (in production prefer workload identity / service account; this env is for CI/tests)

    Without audience the verifier fails closed (UNKNOWN / not trusted).
    Client-supplied verdict lists are never used to raise the tier.
    """

    DECODE_URL = (
        "https://playintegrity.googleapis.com/v1/{package}:decodeIntegrityToken"
    )

    def __init__(
        self,
        *,
        audience: str | None = None,
        package_name: str | None = None,
        cert_digest: str | None = None,
        access_token: str | None = None,
        decoder: TokenDecoder | None = None,
        max_token_age_seconds: int = 300,
    ) -> None:
        self.audience = (audience if audience is not None else os.getenv("SENTINEL_PLAY_INTEGRITY_AUDIENCE") or "").strip()
        self.package_name = (
            package_name
            if package_name is not None
            else os.getenv("SENTINEL_PLAY_INTEGRITY_PACKAGE", "com.alpha0.app")
        ).strip()
        raw_digest = (
            cert_digest
            if cert_digest is not None
            else os.getenv("SENTINEL_PLAY_INTEGRITY_CERT_DIGEST", "")
        )
        self.cert_digest = _normalize_digest(raw_digest) if raw_digest else ""
        self.access_token = (
            access_token
            if access_token is not None
            else os.getenv("SENTINEL_PLAY_INTEGRITY_ACCESS_TOKEN") or ""
        ).strip()
        self.decoder = decoder
        self.max_token_age_seconds = max_token_age_seconds

    def configured(self) -> bool:
        return bool(self.audience)

    def verify(self, integrity_token: str, expected_nonce: str) -> IntegrityVerificationResult:
        if not self.configured():
            return IntegrityVerificationResult(
                tier=IntegrityTier.UNKNOWN,
                reason="PLAY_INTEGRITY_NOT_CONFIGURED",
                trusted=False,
            )
        if not integrity_token or not isinstance(integrity_token, str):
            return IntegrityVerificationResult(
                tier=IntegrityTier.FAILED,
                reason="INTEGRITY_TOKEN_REQUIRED",
                trusted=False,
            )
        if len(integrity_token) > 65536:
            return IntegrityVerificationResult(
                tier=IntegrityTier.FAILED,
                reason="INTEGRITY_TOKEN_MALFORMED",
                trusted=False,
            )
        try:
            payload = self._decode(integrity_token)
        except Exception:
            return IntegrityVerificationResult(
                tier=IntegrityTier.FAILED,
                reason="INTEGRITY_TOKEN_INVALID",
                trusted=False,
            )

        token_payload = payload.get("tokenPayloadExternal") or payload
        request_details = token_payload.get("requestDetails") or {}
        app_integrity = token_payload.get("appIntegrity") or {}
        device_integrity = token_payload.get("deviceIntegrity") or {}

        token_nonce = str(request_details.get("nonce") or "")
        if not expected_nonce or token_nonce != expected_nonce:
            return IntegrityVerificationResult(
                tier=IntegrityTier.FAILED,
                reason="INTEGRITY_NONCE_MISMATCH",
                trusted=False,
            )

        request_package = str(request_details.get("requestPackageName") or app_integrity.get("packageName") or "")
        if self.package_name and request_package and request_package != self.package_name:
            return IntegrityVerificationResult(
                tier=IntegrityTier.FAILED,
                reason="INTEGRITY_PACKAGE_MISMATCH",
                trusted=False,
                package_name=request_package,
            )
        if self.package_name and not request_package:
            return IntegrityVerificationResult(
                tier=IntegrityTier.FAILED,
                reason="INTEGRITY_PACKAGE_MISSING",
                trusted=False,
            )

        certs = app_integrity.get("certificateSha256Digest") or []
        if isinstance(certs, str):
            certs = [certs]
        normalized_certs = {_normalize_digest(str(c)) for c in certs if c}
        if self.cert_digest:
            if not normalized_certs or self.cert_digest not in normalized_certs:
                return IntegrityVerificationResult(
                    tier=IntegrityTier.FAILED,
                    reason="INTEGRITY_CERTIFICATE_MISMATCH",
                    trusted=False,
                    package_name=request_package or None,
                    certificate_digest=next(iter(normalized_certs), None),
                )

        # Freshness: Google returns timestampMillis on requestDetails.
        ts_ms = request_details.get("timestampMillis")
        if ts_ms is not None:
            try:
                age = time.time() - (int(ts_ms) / 1000.0)
                if age > self.max_token_age_seconds or age < -60:
                    return IntegrityVerificationResult(
                        tier=IntegrityTier.FAILED,
                        reason="INTEGRITY_TOKEN_STALE",
                        trusted=False,
                        package_name=request_package or None,
                    )
            except (TypeError, ValueError):
                return IntegrityVerificationResult(
                    tier=IntegrityTier.FAILED,
                    reason="INTEGRITY_TOKEN_MALFORMED",
                    trusted=False,
                )

        app_recognition = str(app_integrity.get("appRecognitionVerdict") or "")
        if app_recognition and app_recognition not in {"PLAY_RECOGNIZED", "UNRECOGNIZED_VERSION"}:
            # UNEVALUATED / other → fail closed for trusted path
            if app_recognition not in {"PLAY_RECOGNIZED", "UNRECOGNIZED_VERSION"}:
                pass
        if app_recognition in {"UNEVALUATED"}:
            return IntegrityVerificationResult(
                tier=IntegrityTier.FAILED,
                reason="INTEGRITY_APP_UNEVALUATED",
                trusted=False,
                package_name=request_package or None,
            )

        verdicts = set(device_integrity.get("deviceRecognitionVerdict") or [])
        tier = classify_verdicts(verdicts)
        if tier is IntegrityTier.UNKNOWN or tier is IntegrityTier.FAILED:
            return IntegrityVerificationResult(
                tier=tier if tier is IntegrityTier.FAILED else IntegrityTier.FAILED,
                reason="INTEGRITY_DEVICE_INSUFFICIENT",
                trusted=False,
                package_name=request_package or None,
                device_recognition_verdict=tuple(sorted(verdicts)),
            )

        return IntegrityVerificationResult(
            tier=tier,
            reason="PLAY_INTEGRITY_VERIFIED",
            trusted=True,
            package_name=request_package or None,
            certificate_digest=next(iter(normalized_certs), None),
            device_recognition_verdict=tuple(sorted(verdicts)),
        )

    def _decode(self, integrity_token: str) -> dict[str, Any]:
        if self.decoder is not None:
            return self.decoder(integrity_token)
        if not self.access_token:
            raise RuntimeError("PLAY_INTEGRITY_ACCESS_TOKEN_MISSING")
        url = self.DECODE_URL.format(package=self.package_name)
        body = json.dumps({"integrityToken": integrity_token}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"PLAY_INTEGRITY_DECODE_HTTP_{exc.code}") from exc
