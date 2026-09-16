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

# Public API errors are selected from explicit constants. Provider/library
# exception text is never reflected verbatim into an HTTP response: doing so
# would couple the public surface to internal exception/stack details and can
# disclose implementation information when providers wrap lower-level errors.
_PROVIDER_VERIFICATION_CODES = frozenset(
    {
        "PROVIDER_WEBHOOK_BODY_INVALID",
        "PROVIDER_WEBHOOK_EVENT_TIME_INVALID",
        "PROVIDER_WEBHOOK_SIGNATURE_INVALID",
        "PROVIDER_WEBHOOK_SIGNATURE_STALE",
        "STRIPE_MODE_MISMATCH",
        "STRIPE_SUBSCRIPTION_BINDING_INVALID",
    }
)
_STRIPE_PROVIDER_CODES = frozenset(
    {
        "STRIPE_API_UNAVAILABLE",
        "STRIPE_API_RESPONSE_TOO_LARGE",
        "STRIPE_API_RESPONSE_INVALID",
        "STRIPE_CHECKOUT_RESPONSE_INVALID",
        "STRIPE_MODE_MISMATCH",
    }
)
_BILLING_CONFLICT_CODES = frozenset(
    {
        "SUBSCRIPTION_STATE_CHANGED",
        "SUBSCRIPTION_PROVIDER_MISMATCH",
        "SUBSCRIPTION_BINDING_MISMATCH",
        "SUBSCRIPTION_ALREADY_EXISTS",
        "INVALID_WEBHOOK_STATE",
    }
)


def _public_code(exc: BaseException, allowed: frozenset[str], fallback: str) -> str:
    """Map an internal exception to a constant allowlisted public code."""

    candidate = exc.args[0] if len(exc.args) == 1 and isinstance(exc.args[0], str) else ""
    for code in allowed:
        if candidate == code:
            return code
    return fallback


class CheckoutSessionRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


@router.post("/v1/billing/checkout-sessions")
def create_checkout_session(
    payload: CheckoutSessionRequest,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, Any]:
    """Create or resume a server-owned Stripe-hosted Checkout session.

    The browser supplies only a canonical SENTINEL plan code. Stripe price IDs,
    mode, redirect URLs and subscription metadata remain server configuration.
    A local PENDING row is created first and never grants paid features. An
    existing unbound PENDING Stripe setup for the same plan is reused so
    cancellation or transient provider failure does not strand the account.
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
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=503, detail="STRIPE_NOT_CONFIGURED") from None
    if adapter is None:
        raise HTTPException(status_code=503, detail="STRIPE_NOT_CONFIGURED")
    if payload.plan_code not in adapter.config.price_ids:
        raise HTTPException(status_code=503, detail="STRIPE_PLAN_NOT_CONFIGURED")

    pending = next(
        (
            item
            for item in store.list_subscriptions(principal.user_id)
            if item.get("provider") == "stripe"
            and item.get("plan_code") == payload.plan_code
            and item.get("status") == "PENDING"
            and item.get("provider_subscription_id") == f"local_{item.get('id')}"
        ),
        None,
    )
    try:
        item = pending or billing_service.create_subscription(
            principal.user_id,
            payload.plan_code,
            provider="stripe",
        )
        checkout = adapter.create_checkout_session(item["id"], payload.plan_code)
    except ValueError as exc:
        code = _public_code(
            exc,
            frozenset({"SUBSCRIPTION_ALREADY_EXISTS", "STRIPE_PLAN_NOT_CONFIGURED"}),
            "BILLING_CHECKOUT_INVALID",
        )
        status = 409 if code == "SUBSCRIPTION_ALREADY_EXISTS" else 400
        raise HTTPException(status_code=status, detail=code) from None
    except StripeProviderError as exc:
        # The retained PENDING row is deliberately non-entitling and makes a
        # later retry deterministic through the same provider idempotency key.
        code = _public_code(exc, _STRIPE_PROVIDER_CODES, "STRIPE_API_ERROR")
        raise HTTPException(status_code=502, detail=code) from None

    store.add_audit({
        "actor_user_id": principal.user_id,
        "actor_device_id": principal.device_id,
        "action": "billing:checkout:create",
        "resource": item["id"],
        "decision": "ALLOW",
        "reason_code": "STRIPE_TEST_CHECKOUT_CREATED" if not checkout.livemode else "STRIPE_CHECKOUT_CREATED",
        "request_id": rid,
        "metadata": {"resumed": pending is not None},
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
    except (KeyError, RuntimeError, ValueError):
        raise HTTPException(status_code=503, detail="BILLING_PROVIDER_NOT_CONFIGURED") from None

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
        reason = _public_code(exc, frozenset({"STRIPE_EVENT_IGNORED"}), "PROVIDER_EVENT_IGNORED")
        return {"accepted": False, "ignored": True, "reason": reason}
    except ProviderVerificationError as exc:
        code = _public_code(exc, _PROVIDER_VERIFICATION_CODES, "PROVIDER_WEBHOOK_VERIFICATION_FAILED")
        raise HTTPException(status_code=401, detail=code) from None
    except ValueError:
        raise HTTPException(status_code=400, detail="PROVIDER_WEBHOOK_INVALID") from None
    try:
        result = billing_service.apply_verified_webhook(verified)
    except ValueError as exc:
        candidate = exc.args[0] if len(exc.args) == 1 and isinstance(exc.args[0], str) else ""
        if candidate == "SUBSCRIPTION_NOT_FOUND":
            status = 404
            code = "SUBSCRIPTION_NOT_FOUND"
        elif candidate in _BILLING_CONFLICT_CODES:
            status = 409
            code = _public_code(exc, _BILLING_CONFLICT_CODES, "SUBSCRIPTION_CONFLICT")
        elif candidate.startswith("INVALID_BILLING_TRANSITION"):
            status = 409
            code = "INVALID_BILLING_TRANSITION"
        else:
            status = 400
            code = "BILLING_WEBHOOK_INVALID"
        raise HTTPException(status_code=status, detail=code) from None
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
