from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

from fastapi import HTTPException, Request

ADMIN_LOCKOUT_THRESHOLD = int(os.getenv("SENTINEL_ADMIN_LOCKOUT_THRESHOLD", "5"))
_TOTP_STEP_SECONDS = 30
_TOTP_DIGITS = 6
_TOTP_WINDOW = 1


def _decode_totp_secret(secret: str) -> bytes:
    normalized = "".join(secret.split()).replace("-", "").upper()
    if not normalized:
        raise ValueError("empty TOTP secret")
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    key = base64.b32decode(normalized + padding, casefold=True)
    if len(key) < 16:
        raise ValueError("TOTP secret must contain at least 128 bits")
    return key


def _totp_at(key: bytes, counter: int) -> str:
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    dynamic = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return f"{dynamic % (10 ** _TOTP_DIGITS):0{_TOTP_DIGITS}d}"


def verify_totp(secret: str, code: str | None, *, now: float | None = None) -> bool:
    provided = (code or "").strip()
    if len(provided) != _TOTP_DIGITS or not provided.isdigit():
        return False
    try:
        key = _decode_totp_secret(secret)
    except (ValueError, TypeError):
        return False
    current_counter = int((time.time() if now is None else now) // _TOTP_STEP_SECONDS)
    for offset in range(-_TOTP_WINDOW, _TOTP_WINDOW + 1):
        if hmac.compare_digest(provided, _totp_at(key, current_counter + offset)):
            return True
    return False


def require_admin(x_sentinel_admin_token: str | None, request: Request, store) -> None:
    expected = os.getenv("SENTINEL_ADMIN_TOKEN")
    totp_secret = os.getenv("SENTINEL_ADMIN_TOTP_SECRET")
    if not expected or not totp_secret:
        raise HTTPException(status_code=503, detail="ADMIN_CONTROL_PLANE_NOT_CONFIGURED")

    subject = f"admin:{(request.client.host if request.client else 'unknown')}"
    if store.security_failure_count(subject) >= ADMIN_LOCKOUT_THRESHOLD:
        store.add_audit(
            {
                "actor_user_id": None,
                "actor_device_id": None,
                "action": "admin:auth",
                "resource": "admin",
                "decision": "DENY",
                "reason_code": "ADMIN_LOCKED",
                "request_id": None,
            }
        )
        raise HTTPException(status_code=403, detail="ADMIN_ACCESS_DENIED")

    provided_token = x_sentinel_admin_token or ""
    token_valid = bool(provided_token) and hmac.compare_digest(provided_token, expected)
    totp_valid = verify_totp(totp_secret, request.headers.get("X-Sentinel-Admin-TOTP"))
    if not token_valid or not totp_valid:
        store.record_security_failure(subject, "admin")
        store.add_audit(
            {
                "actor_user_id": None,
                "actor_device_id": None,
                "action": "admin:auth",
                "resource": "admin",
                "decision": "DENY",
                "reason_code": "ADMIN_MFA_DENIED" if token_valid else "ADMIN_ACCESS_DENIED",
                "request_id": None,
            }
        )
        raise HTTPException(status_code=403, detail="ADMIN_ACCESS_DENIED")

    store.add_audit(
        {
            "actor_user_id": None,
            "actor_device_id": None,
            "action": "admin:auth",
            "resource": "admin",
            "decision": "ALLOW",
            "reason_code": "ADMIN_MFA_VALID",
            "request_id": None,
        }
    )
