from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import UTC, datetime
from typing import Any

from app.core.billing_provider import ProviderVerificationError, VerifiedBillingWebhook
from app.core.json_bounds import validate_bounded_json
from app.core.p1_runtime import BillingState

_STRIPE_ID = re.compile(r"^[A-Za-z0-9_:-]{3,255}$")
_SUPPORTED_EVENTS = frozenset(
    {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
)
_STATUS_MAP = {
    "active": BillingState.ACTIVE,
    "trialing": BillingState.ACTIVE,
    "past_due": BillingState.PAST_DUE,
    "unpaid": BillingState.PAST_DUE,
    "paused": BillingState.PAST_DUE,
    "incomplete": BillingState.PAST_DUE,
    "incomplete_expired": BillingState.EXPIRED,
    "canceled": BillingState.CANCELED,
}


class StripeSandboxWebhookAdapter:
    """Stripe subscription webhook verifier for the pre-release sandbox.

    The adapter intentionally accepts test-mode events only by default. It
    verifies the exact raw request bytes using Stripe's timestamped v1 HMAC
    signature contract and translates only subscription lifecycle events into
    SENTINEL's provider-neutral billing state machine.
    """

    provider_id = "stripe"

    def __init__(
        self,
        webhook_secret: str,
        *,
        expected_livemode: bool = False,
        max_clock_skew_seconds: int = 300,
    ) -> None:
        secret = webhook_secret.encode("utf-8")
        if len(secret) < 16:
            raise ValueError("STRIPE_WEBHOOK_SECRET_TOO_SHORT")
        if max_clock_skew_seconds <= 0:
            raise ValueError("INVALID_PROVIDER_CLOCK_SKEW")
        self._secret = secret
        self._expected_livemode = expected_livemode
        self._max_clock_skew_seconds = max_clock_skew_seconds

    def verify_webhook(
        self,
        body: bytes,
        signature: str,
        *,
        now: datetime | None = None,
    ) -> VerifiedBillingWebhook:
        if not body or len(body) > 262_144:
            raise ProviderVerificationError("STRIPE_WEBHOOK_BODY_INVALID")
        timestamp, signatures = _parse_stripe_signature(signature)
        current = now or datetime.now(UTC)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("PROVIDER_VERIFIER_TIME_MUST_BE_AWARE")
        if abs(int(current.timestamp()) - timestamp) > self._max_clock_skew_seconds:
            raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_STALE")
        expected = hmac.new(
            self._secret,
            str(timestamp).encode("ascii") + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        if not any(hmac.compare_digest(candidate, expected) for candidate in signatures):
            raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_INVALID")

        try:
            raw = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderVerificationError("STRIPE_WEBHOOK_BODY_INVALID") from exc
        if not isinstance(raw, dict):
            raise ProviderVerificationError("STRIPE_WEBHOOK_BODY_INVALID")
        try:
            validate_bounded_json(raw, max_bytes=262_144, max_depth=10, max_nodes=4096)
        except ValueError as exc:
            raise ProviderVerificationError("STRIPE_WEBHOOK_BODY_INVALID") from exc

        event_id = raw.get("id")
        event_type = raw.get("type")
        livemode = raw.get("livemode")
        created = raw.get("created")
        if not isinstance(event_id, str) or not _STRIPE_ID.fullmatch(event_id):
            raise ProviderVerificationError("STRIPE_EVENT_ID_INVALID")
        if event_type not in _SUPPORTED_EVENTS:
            raise ProviderVerificationError("STRIPE_EVENT_TYPE_UNSUPPORTED")
        if not isinstance(livemode, bool) or livemode is not self._expected_livemode:
            raise ProviderVerificationError("STRIPE_LIVEMODE_MISMATCH")
        if not isinstance(created, int) or created <= 0:
            raise ProviderVerificationError("STRIPE_EVENT_TIME_INVALID")

        data = raw.get("data")
        subscription = data.get("object") if isinstance(data, dict) else None
        if not isinstance(subscription, dict) or subscription.get("object") != "subscription":
            raise ProviderVerificationError("STRIPE_SUBSCRIPTION_OBJECT_INVALID")
        subscription_id = subscription.get("id")
        customer_id = subscription.get("customer")
        status = subscription.get("status")
        if not isinstance(subscription_id, str) or not _STRIPE_ID.fullmatch(subscription_id):
            raise ProviderVerificationError("STRIPE_SUBSCRIPTION_ID_INVALID")
        if customer_id is not None and (
            not isinstance(customer_id, str) or not _STRIPE_ID.fullmatch(customer_id)
        ):
            raise ProviderVerificationError("STRIPE_CUSTOMER_ID_INVALID")
        target = BillingState.CANCELED if event_type == "customer.subscription.deleted" else _STATUS_MAP.get(status)
        if target is None:
            raise ProviderVerificationError("STRIPE_SUBSCRIPTION_STATUS_UNSUPPORTED")

        occurred_at = datetime.fromtimestamp(created, UTC)
        return VerifiedBillingWebhook(
            event_id=event_id,
            provider=self.provider_id,
            provider_subscription_id=subscription_id,
            target_state=target,
            occurred_at=occurred_at,
            external_reference=customer_id,
            payload={
                "stripe_event_type": event_type,
                "stripe_subscription_status": str(status or "canceled"),
                "livemode": livemode,
            },
            verification_method="stripe-signature-v1",
            verified_at=current.astimezone(UTC),
        )


def configured_stripe_sandbox_adapter() -> StripeSandboxWebhookAdapter:
    secret = os.getenv("SENTINEL_STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise RuntimeError("STRIPE_SANDBOX_NOT_CONFIGURED")
    livemode_text = os.getenv("SENTINEL_STRIPE_EXPECT_LIVEMODE", "false").strip().lower()
    if livemode_text not in {"true", "false"}:
        raise RuntimeError("SENTINEL_STRIPE_EXPECT_LIVEMODE must be true or false")
    if livemode_text == "true":
        # SENTINEL pre-release intentionally does not permit live Stripe.
        raise RuntimeError("STRIPE_LIVE_MODE_DISABLED_PRE_RELEASE")
    return StripeSandboxWebhookAdapter(secret, expected_livemode=False)


def _parse_stripe_signature(value: str) -> tuple[int, tuple[str, ...]]:
    if not value or len(value) > 2048:
        raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_INVALID")
    timestamp: int | None = None
    signatures: list[str] = []
    for piece in value.split(","):
        key, separator, raw = piece.strip().partition("=")
        if not separator:
            raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_INVALID")
        if key == "t":
            if timestamp is not None:
                raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_INVALID")
            try:
                timestamp = int(raw)
            except ValueError as exc:
                raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_INVALID") from exc
        elif key == "v1":
            digest = raw.lower()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_INVALID")
            signatures.append(digest)
        # Stripe can add other signature schemes; they are ignored, never trusted.
    if timestamp is None or not signatures:
        raise ProviderVerificationError("STRIPE_WEBHOOK_SIGNATURE_INVALID")
    return timestamp, tuple(signatures)
