from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.billing import PLANS_BY_CODE
from app.core.billing_provider import (
    ProviderEventIgnored,
    ProviderVerificationError,
    configured_provider_registry,
)
from app.core.stripe_billing import StripeProviderError, configured_stripe_adapter

router = APIRouter(tags=["billing-provider"])
_PROVIDER_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class CheckoutSessionRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


@router.post("/v1/billing/checkout-sessions")
def create_checkout_session(
    payload: CheckoutSessionRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, Any]:
    """Create a server-owned Stripe-hosted subscription Checkout session.

    The browser supplies only a canonical SENTINEL plan code. Stripe price IDs,
    mode, redirect URLs and subscription metadata remain server configuration.
    A local PENDING row is created first and never grants paid features.
    """

    from app.main import (
        authorize_request,
        billing_service,
        principal_from_token,
        rate_limit,
        request_id,
        require_bearer,
        store,
    )

    rate_limit(request, "billing-checkout")
    rid = request_id(request, x_request_id)
    principal = principal_from_token(require_bearer(authorization_header))
    authorize_request(principal, "billing:write", "billing:checkout", rid)

    plan = PLANS_BY_CODE.get(payload.plan_code)
    if plan is None:
        raise HTTPException(status_code=400, detail="UNKNOWN_PLAN")
    if plan.amount_minor <= 0:
        raise HTTPException(status_code=400, detail="FREE_PLAN_REQUIRES_NO_CHECKOUT")
    try:
        adapter = configured_stripe_adapter()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="STRIPE_NOT_CONFIGURED") from exc
    if adapter is None:
        raise HTTPException(status_code=503, detail="STRIPE_NOT_CONFIGURED")
    if payload.plan_code not in adapter.config.price_ids:
        raise HTTPException(status_code=503, detail="STRIPE_PLAN_NOT_CONFIGURED")

    try:
        item = billing_service.create_subscription(
            principal.user_id,
            payload.plan_code,
            provider="stripe",
        )
        checkout = adapter.create_checkout_session(item["id"], payload.plan_code)
    except ValueError as exc:
        code = str(exc)
        status = 409 if code == "SUBSCRIPTION_ALREADY_EXISTS" else 400
        raise HTTPException(status_code=status, detail=code) from exc
    except StripeProviderError as exc:
        # The PENDING row intentionally grants no feature. Keeping the failed
        # setup attempt is safer than fabricating provider confirmation.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    store.add_audit({
        "actor_user_id": principal.user_id,
        "actor_device_id": principal.device_id,
        "action": "billing:checkout:create",
        "resource": item["id"],
        "decision": "ALLOW",
        "reason_code": "STRIPE_TEST_CHECKOUT_CREATED" if not checkout.livemode else "STRIPE_CHECKOUT_CREATED",
        "request_id": rid,
    })
    return {
        "provider": "stripe",
        "subscription_id": item["id"],
        "checkout_session_id": checkout.session_id,
        "checkout_url": checkout.checkout_url,
        "livemode": checkout.livemode,
    }


@router.post("/v1/billing/provider-webhooks/{provider}")
async def verified_provider_webhook(
    provider: str,
    request: Request,
    x_billing_signature: str | None = Header(default=None, alias="X-Billing-Signature"),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, Any]:
    """Accept only cryptographically verified provider events.

    Stripe uses its native ``Stripe-Signature`` header. The generic signed
    provider adapter retains ``X-Billing-Signature``. Neither may fall back to
    the legacy shared-token webhook boundary.
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

    if provider == "stripe":
        if not stripe_signature:
            raise HTTPException(status_code=401, detail="PROVIDER_WEBHOOK_SIGNATURE_REQUIRED")
        signature = stripe_signature
    else:
        if not x_billing_signature:
            raise HTTPException(status_code=401, detail="PROVIDER_WEBHOOK_SIGNATURE_REQUIRED")
        signature = x_billing_signature

    body = await request.body()
    if len(body) > 262_144:
        raise HTTPException(status_code=413, detail="PROVIDER_WEBHOOK_BODY_TOO_LARGE")
    try:
        verified = adapter.verify_webhook(body, signature)
    except ProviderEventIgnored as exc:
        return {"accepted": False, "ignored": True, "reason": str(exc)}
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
            "SUBSCRIPTION_PROVIDER_MISMATCH",
            "SUBSCRIPTION_ALREADY_EXISTS",
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
