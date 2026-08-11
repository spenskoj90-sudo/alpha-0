from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def require_admin(x_sentinel_admin_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("SENTINEL_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_CONTROL_PLANE_NOT_CONFIGURED")
    if not x_sentinel_admin_token or not hmac.compare_digest(x_sentinel_admin_token, expected):
        raise HTTPException(status_code=403, detail="ADMIN_ACCESS_DENIED")
