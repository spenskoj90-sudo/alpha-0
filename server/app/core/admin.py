from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

from app.core.totp import (
    decode_totp_secret as _decode_totp_secret,
    totp_at as _totp_at,
    verify_totp,
)

ADMIN_LOCKOUT_THRESHOLD = int(os.getenv("SENTINEL_ADMIN_LOCKOUT_THRESHOLD", "5"))


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
