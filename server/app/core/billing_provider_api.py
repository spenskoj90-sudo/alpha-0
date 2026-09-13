from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.billing_provider import ProviderVerificationError, configured_provider_registry

router = APIRouter(tags=["billing-provider"])
_PROVIDER_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@router.post("/v1/billing/provider-webhooks/{provider}")
async def verified_provider_webhook(
    provider: str,
    request: Request,
    x_billing_signature: str | None = Header(default=None, alias="X-Billing-Signature"),
) -> dict[str, Any]:
    """Accept only cryptographically verified provider events.

    This endpoint is distinct from the legacy/internal shared-token webhook.
    Production providers must enter through a registered verifier adapter and
    may not fall back to the generic token boundary.
    """

    if not _PROVIDER_ID.fullmatch(provider):
        raise HTTPException(status_code=400, detail="INVALID_PROVIDER")
    from app.main import billing_service, rate_limit, store

    rate_limit(request, "billing-provider-webhook")
    try:
        registry = configured_provider_registry()
        adapter = registry.require(provider)
    except (KeyError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="BILLING_PROVIDER_NOT_CONFIGURED") from exc
    if not x_billing_signature:
        raise HTTPException(status_code=401, detail="PROVIDER_WEBHOOK_SIGNATURE_REQUIRED")
    body = await request.body()
    if len(body) > 262_144:
        raise HTTPException(status_code=413, detail="PROVIDER_WEBHOOK_BODY_TOO_LARGE")
    try:
        verified = adapter.verify_webhook(body, x_billing_signature)
    except ProviderVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        result = billing_service.apply_verified_webhook(verified)
    except ValueError as exc:
        code = str(exc)
        status = 404 if code == "SUBSCRIPTION_NOT_FOUND" else 409 if code in {
            "SUBSCRIPTION_STATE_CHANGED",
            "INVALID_WEBHOOK_STATE",
        } or code.startswith("INVALID_BILLING_TRANSITION") else 400
        raise HTTPException(status_code=status, detail=code) from exc
    subscription = result["subscription"]
    store.add_audit({
        "actor_user_id": subscription["user_id"],
        "actor_device_id": None,
        "action": "billing:webhook:verified",
        "resource": provider,
        "decision": "ALLOW",
        "reason_code": verified.verification_method,
        "request_id": None,
    })
    return result


@router.get("/v1/billing/features")
def billing_features(
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, Any]:
    """Return server-derived feature grants from active subscriptions only."""

    from app.main import (
        authorize_request,
        billing_service,
        principal_from_token,
        request_id,
        require_bearer,
    )

    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "billing:read", "billing:features", rid)
    return {"features": list(billing_service.feature_entitlements(principal.user_id))}
