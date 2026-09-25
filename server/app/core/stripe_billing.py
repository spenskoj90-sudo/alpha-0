from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from app.core.billing_provider import (
    ProviderEventIgnored,
    ProviderSubscriptionSnapshot,
    ProviderVerificationError,
    VerifiedBillingWebhook,
)
from app.core.p1_runtime import BillingState

_STRIPE_API_BASE = "https://api.stripe.com/v1"
_STRIPE_PROVIDER = "stripe"
_MAX_WEBHOOK_BYTES = 262_144
_MAX_API_RESPONSE_BYTES = 1_048_576
_ID = re.compile(r"^[A-Za-z0-9_:-]{3,256}$")


class StripeProviderError(RuntimeError):
    """A bounded Stripe API/configuration failure safe for application handling."""


class StripeTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        fields: Mapping[str, str] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class StripeConfig:
    secret_key: str = field(repr=False)
    webhook_secret: str = field(repr=False)
    price_ids: Mapping[str, str]
    success_url: str
    cancel_url: str
    livemode: bool = False
    max_clock_skew_seconds: int = 300

    def __post_init__(self) -> None:
        expected_key_prefix = "sk_live_" if self.livemode else "sk_test_"
        if not self.secret_key.startswith(expected_key_prefix) or len(self.secret_key) < len(expected_key_prefix) + 8:
            raise ValueError("STRIPE_SECRET_KEY_MODE_MISMATCH")
        if not self.webhook_secret.startswith("whsec_") or len(self.webhook_secret) < 16:
            raise ValueError("STRIPE_WEBHOOK_SECRET_INVALID")
        if self.max_clock_skew_seconds <= 0 or self.max_clock_skew_seconds > 3600:
            raise ValueError("STRIPE_WEBHOOK_CLOCK_SKEW_INVALID")
        if not self.price_ids:
            raise ValueError("STRIPE_PRICE_MAPPING_REQUIRED")
        for plan, price_id in self.price_ids.items():
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", plan):
                raise ValueError("STRIPE_PLAN_MAPPING_INVALID")
            if not re.fullmatch(r"price_[A-Za-z0-9]{6,128}", price_id):
                raise ValueError("STRIPE_PRICE_MAPPING_INVALID")
        _validate_checkout_url(self.success_url)
        _validate_checkout_url(self.cancel_url)


@dataclass(frozen=True)
class StripeCheckoutSession:
    session_id: str
    checkout_url: str
    livemode: bool


class StripeHttpTransport:
    """Narrow form-encoded Stripe REST client with bounded responses."""

    def __init__(self, secret_key: str, *, timeout_seconds: float = 10.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 30:
            raise ValueError("STRIPE_TIMEOUT_INVALID")
        self._secret_key = secret_key
        self._timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        fields: Mapping[str, str] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        normalized_method = method.upper()
        if normalized_method not in {"GET", "POST"}:
            raise ValueError("STRIPE_METHOD_INVALID")
        if not path.startswith("/") or ".." in path:
            raise ValueError("STRIPE_PATH_INVALID")

        encoded = urlencode(dict(fields or {})).encode("utf-8")
        url = f"{_STRIPE_API_BASE}{path}"
        body: bytes | None = encoded if normalized_method == "POST" else None
        if normalized_method == "GET" and encoded:
            url = f"{url}?{encoded.decode('ascii')}"
        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "Accept": "application/json",
            "User-Agent": "sentinel-core/stripe-adapter",
        }
        if normalized_method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if idempotency_key:
            if not re.fullmatch(r"[A-Za-z0-9._:-]{8,200}", idempotency_key):
                raise ValueError("STRIPE_IDEMPOTENCY_KEY_INVALID")
            headers["Idempotency-Key"] = idempotency_key

        request = Request(url=url, data=body, method=normalized_method, headers=headers)
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read(_MAX_API_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise StripeProviderError(f"STRIPE_API_HTTP_{exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise StripeProviderError("STRIPE_API_UNAVAILABLE") from exc
        if len(raw) > _MAX_API_RESPONSE_BYTES:
            raise StripeProviderError("STRIPE_API_RESPONSE_TOO_LARGE")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StripeProviderError("STRIPE_API_RESPONSE_INVALID") from exc
        if not isinstance(payload, dict):
            raise StripeProviderError("STRIPE_API_RESPONSE_INVALID")
        return payload


class StripeBillingProviderAdapter:
    """Stripe Billing adapter; entitlements still come only from Core state."""

    provider_id = _STRIPE_PROVIDER

    def __init__(self, config: StripeConfig, transport: StripeTransport | None = None) -> None:
        self.config = config
        self._transport = transport or StripeHttpTransport(config.secret_key)

    def create_checkout_session(self, local_subscription_id: str, plan_code: str) -> StripeCheckoutSession:
        _validate_local_subscription_id(local_subscription_id)
        price_id = self.config.price_ids.get(plan_code)
        if price_id is None:
            raise ValueError("STRIPE_PLAN_NOT_CONFIGURED")
        payload = self._transport.request(
            "POST",
            "/checkout/sessions",
            {
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "success_url": self.config.success_url,
                "cancel_url": self.config.cancel_url,
                "client_reference_id": local_subscription_id,
                "metadata[sentinel_subscription_id]": local_subscription_id,
                "subscription_data[metadata][sentinel_subscription_id]": local_subscription_id,
            },
            idempotency_key=f"sentinel-checkout:{local_subscription_id}",
        )
        session_id = payload.get("id")
        checkout_url = payload.get("url")
        livemode = payload.get("livemode")
        if not isinstance(session_id, str) or not session_id.startswith("cs_") or len(session_id) > 256:
            raise StripeProviderError("STRIPE_CHECKOUT_RESPONSE_INVALID")
        if not isinstance(checkout_url, str) or not _is_https_url(checkout_url):
            raise StripeProviderError("STRIPE_CHECKOUT_RESPONSE_INVALID")
        if not isinstance(livemode, bool) or livemode != self.config.livemode:
            raise StripeProviderError("STRIPE_MODE_MISMATCH")
        return StripeCheckoutSession(session_id=session_id, checkout_url=checkout_url, livemode=livemode)

    def verify_webhook(
        self,
        body: bytes,
        signature: str,
        *,
        now: datetime | None = None,
    ) -> VerifiedBillingWebhook:
        if not body or len(body) > _MAX_WEBHOOK_BYTES:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        timestamp, signatures = _parse_stripe_signature(signature)
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            raise ValueError("PROVIDER_VERIFIER_TIME_MUST_BE_AWARE")
        if abs(int(current.timestamp()) - timestamp) > self.config.max_clock_skew_seconds:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_STALE")
        expected = hmac.new(
            self.config.webhook_secret.encode("utf-8"),
            str(timestamp).encode("ascii") + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        if not any(hmac.compare_digest(candidate, expected) for candidate in signatures):
            raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")

        try:
            event = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID") from exc
        if not isinstance(event, dict):
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        if event.get("livemode") is not self.config.livemode:
            raise ProviderVerificationError("STRIPE_MODE_MISMATCH")

        event_id = event.get("id")
        event_type = event.get("type")
        created = event.get("created")
        data = event.get("data")
        if not isinstance(event_id, str) or not event_id.startswith("evt_") or len(event_id) > 256:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        if not isinstance(event_type, str) or len(event_type) > 128:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        if event_type not in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            raise ProviderEventIgnored("STRIPE_EVENT_IGNORED")
        if not isinstance(created, int) or created <= 0:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_EVENT_TIME_INVALID")
        if not isinstance(data, dict) or not isinstance(data.get("object"), dict):
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        subscription = data["object"]
        subscription_id = subscription.get("id")
        status = subscription.get("status")
        metadata_value = subscription.get("metadata")
        metadata = {} if metadata_value is None else metadata_value
        if not isinstance(subscription_id, str) or not subscription_id.startswith("sub_") or len(subscription_id) > 256:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        if not isinstance(status, str) or len(status) > 64 or not isinstance(metadata, dict):
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        local_subscription_id = metadata.get("sentinel_subscription_id")
        if local_subscription_id is not None:
            if not isinstance(local_subscription_id, str):
                raise ProviderVerificationError("STRIPE_SUBSCRIPTION_BINDING_INVALID")
            _validate_local_subscription_id(local_subscription_id, verification_error=True)

        target = BillingState.CANCELED if event_type == "customer.subscription.deleted" else _map_stripe_status(status)
        try:
            occurred_at = datetime.fromtimestamp(created, UTC)
        except (OverflowError, OSError, ValueError) as exc:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_EVENT_TIME_INVALID") from exc
        return VerifiedBillingWebhook(
            event_id=event_id,
            provider=self.provider_id,
            provider_subscription_id=subscription_id,
            target_state=target,
            occurred_at=occurred_at,
            external_reference=event_id,
            payload={"event_type": event_type, "stripe_status": status},
            verification_method="stripe-signature-v1",
            verified_at=current.astimezone(UTC),
            local_subscription_id=local_subscription_id,
        )

    def read_subscription(self, provider_subscription_id: str) -> ProviderSubscriptionSnapshot:
        if not re.fullmatch(r"sub_[A-Za-z0-9]{3,252}", provider_subscription_id):
            raise ValueError("INVALID_PROVIDER_SUBSCRIPTION_ID")
        raw = self._transport.request("GET", f"/subscriptions/{quote(provider_subscription_id, safe='')}")
        returned_id = raw.get("id")
        status = raw.get("status")
        livemode = raw.get("livemode")
        if returned_id != provider_subscription_id or not isinstance(status, str):
            raise StripeProviderError("STRIPE_SUBSCRIPTION_RESPONSE_INVALID")
        if not isinstance(livemode, bool) or livemode != self.config.livemode:
            raise StripeProviderError("STRIPE_MODE_MISMATCH")
        target = _map_stripe_status(status)
        revision_material = json.dumps(
            {
                "id": returned_id,
                "status": status,
                "current_period_end": raw.get("current_period_end"),
                "cancel_at_period_end": raw.get("cancel_at_period_end"),
                "canceled_at": raw.get("canceled_at"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        revision = hashlib.sha256(revision_material).hexdigest()
        return ProviderSubscriptionSnapshot(
            provider=self.provider_id,
            provider_subscription_id=provider_subscription_id,
            target_state=target,
            observed_at=datetime.now(UTC),
            revision=revision,
            payload={"stripe_status": status},
        )


def configured_stripe_adapter() -> StripeBillingProviderAdapter | None:
    enabled = _strict_env_bool("SENTINEL_STRIPE_ENABLED", default=False)
    if not enabled:
        return None

    livemode = _strict_env_bool("SENTINEL_STRIPE_LIVEMODE", default=False)
    environment = os.getenv("SENTINEL_ENV", "development").strip().lower()
    if livemode and (environment != "production" or not _strict_env_bool("SENTINEL_STRIPE_ALLOW_LIVE", default=False)):
        raise RuntimeError("STRIPE_LIVE_MODE_NOT_AUTHORIZED")

    required = {
        "secret_key": os.getenv("SENTINEL_STRIPE_SECRET_KEY", ""),
        "webhook_secret": os.getenv("SENTINEL_STRIPE_WEBHOOK_SECRET", ""),
        "core_plus_price": os.getenv("SENTINEL_STRIPE_CORE_PLUS_PRICE_ID", ""),
        "success_url": os.getenv("SENTINEL_STRIPE_SUCCESS_URL", ""),
        "cancel_url": os.getenv("SENTINEL_STRIPE_CANCEL_URL", ""),
    }
    if any(not value for value in required.values()):
        raise RuntimeError("STRIPE_NOT_CONFIGURED")
    try:
        config = StripeConfig(
            secret_key=required["secret_key"],
            webhook_secret=required["webhook_secret"],
            price_ids={"core-plus": required["core_plus_price"]},
            success_url=required["success_url"],
            cancel_url=required["cancel_url"],
            livemode=livemode,
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return StripeBillingProviderAdapter(config)


def _strict_env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RuntimeError(f"{name}_INVALID")


def _parse_stripe_signature(signature: str) -> tuple[int, tuple[str, ...]]:
    if not signature or len(signature) > 2048:
        raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
    timestamp: int | None = None
    signatures: list[str] = []
    for piece in signature.split(","):
        key, separator, value = piece.strip().partition("=")
        if not separator:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
        if key == "t":
            if timestamp is not None:
                raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID") from exc
        elif key == "v1":
            digest = value.lower()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
            signatures.append(digest)
    if timestamp is None or not signatures:
        raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
    return timestamp, tuple(signatures)


def _map_stripe_status(status: str) -> BillingState:
    if status in {"active", "trialing"}:
        return BillingState.ACTIVE
    if status in {"past_due", "unpaid", "incomplete", "paused"}:
        return BillingState.PAST_DUE
    if status == "canceled":
        return BillingState.CANCELED
    if status == "incomplete_expired":
        return BillingState.EXPIRED
    raise ProviderVerificationError("STRIPE_SUBSCRIPTION_STATUS_UNSUPPORTED")


def _validate_local_subscription_id(value: str, *, verification_error: bool = False) -> None:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        error = ProviderVerificationError("STRIPE_SUBSCRIPTION_BINDING_INVALID") if verification_error else ValueError("STRIPE_SUBSCRIPTION_BINDING_INVALID")
        raise error from exc
    if str(parsed) != value.lower():
        error = ProviderVerificationError("STRIPE_SUBSCRIPTION_BINDING_INVALID") if verification_error else ValueError("STRIPE_SUBSCRIPTION_BINDING_INVALID")
        raise error


def _validate_checkout_url(value: str) -> None:
    if not _is_https_url(value):
        raise ValueError("STRIPE_CHECKOUT_URL_INVALID")


def _is_https_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme == "https" and bool(parts.hostname) and parts.username is None and parts.password is None
