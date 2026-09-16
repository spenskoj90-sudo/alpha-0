from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.account_lifecycle import AccountLifecycleService

router = APIRouter(tags=["account"])


class AccountEraseRequest(BaseModel):
    password: str = Field(min_length=12, max_length=256)
    confirmation: Literal["ERASE"]


def _principal(authorization_header: str):
    from app.main import principal_from_token, require_bearer
    return principal_from_token(require_bearer(authorization_header))


@router.get("/v1/account/export")
def account_export(
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
):
    from app.main import rate_limit, store, user_store
    rate_limit(request, "account-export")
    principal = _principal(authorization_header)
    try:
        return AccountLifecycleService(store, user_store).export(principal.user_id)
    except ValueError as exc:
        code = str(exc)
        status = 404 if code == "ACCOUNT_NOT_FOUND" else 413 if code == "ACCOUNT_EXPORT_TOO_LARGE" else 400
        raise HTTPException(status_code=status, detail=code) from exc


@router.post("/v1/account/erase")
def account_erase(
    payload: AccountEraseRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
):
    from app.main import rate_limit, store, user_store
    rate_limit(request, "account-erase")
    principal = _principal(authorization_header)
    # Record intent while the original identity still resolves to its durable id.
    store.add_audit({
        "actor_user_id": principal.user_id,
        "actor_device_id": principal.device_id,
        "action": "account:erase",
        "resource": "account",
        "decision": "ALLOW",
        "reason_code": "REAUTH_REQUIRED_AND_CONFIRMED",
        "request_id": None,
    })
    try:
        return AccountLifecycleService(store, user_store).erase(principal.user_id, payload.password)
    except ValueError as exc:
        code = str(exc)
        status = 403 if code == "ACCOUNT_REAUTH_FAILED" else 400
        raise HTTPException(status_code=status, detail=code) from exc
