from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

ADMIN_LOCKOUT_THRESHOLD = int(os.getenv("SENTINEL_ADMIN_LOCKOUT_THRESHOLD", "5"))


def require_admin(x_sentinel_admin_token: str | None, request: Request, store) -> None:
    expected = os.getenv("SENTINEL_ADMIN_TOKEN")
    if not expected:
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
    provided = x_sentinel_admin_token or ""
    if not provided or not hmac.compare_digest(provided, expected):
        store.record_security_failure(subject, "admin")
        store.add_audit(
            {
                "actor_user_id": None,
                "actor_device_id": None,
                "action": "admin:auth",
                "resource": "admin",
                "decision": "DENY",
                "reason_code": "ADMIN_ACCESS_DENIED",
                "request_id": None,
            }
        )
        raise HTTPException(status_code=403, detail="ADMIN_ACCESS_DENIED")
