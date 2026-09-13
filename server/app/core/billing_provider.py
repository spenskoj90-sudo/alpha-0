from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Protocol

from pydantic import ValidationError

from app.core.models import BillingWebhookRequest
from app.core.p1_runtime import BillingState

_PROVIDER_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class ProviderVerificationError(ValueError):
    """A provider event failed cryptographic or freshness verification."""


@dataclass(frozen=True)
class VerifiedBillingWebhook:
    event_id: str
    provider: str
    provider_subscription_id: str
    target_state: BillingState
    occurred_at: datetime
    external_reference: str | None
    payload: dict[str, object]
    verification_method: str
    verified_at: datetime


@dataclass(frozen=True)
class ProviderSubscriptionSnapshot:
    provider: str
    provider_subscription_id: str
    target_state: BillingState
    observed_at: datetime
    revision: str
    external_reference: str | None = None
    payload: dict[str, object] | None = None

    def reconciliation_event_id(self) -> str:
        material = "\x00".join(
            (
                self.provider,
                self.provider_subscription_id,
                self.revision,
                self.target_state.value,
            )
        )
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return f"reconcile:{digest}"


class BillingProviderAdapter(Protocol):
    provider_id: str

    def verify_webhook(
        self,
        body: bytes,
        signature: str,
        *,
        now: datetime | None = None,
    ) -> VerifiedBillingWebhook: ...

    def read_subscription(self, provider_subscription_id: str) -> ProviderSubscriptionSnapshot: ...


class HmacBillingProviderAdapter:
    """Concrete signed-JSON provider boundary.

    The signature format is ``t=<unix-seconds>,v1=<hex-hmac-sha256>`` and the
    MAC input is the exact byte sequence ``<timestamp>.<raw-body>``.  This is a
    real cryptographic verification boundary, but it deliberately does not
    claim compatibility with Stripe or any other vendor-specific wire format.
    A selected production provider can implement ``BillingProviderAdapter``
    without changing BillingService lifecycle semantics.
    """

    def __init__(
        self,
        provider_id: str,
        secret: bytes,
        *,
        max_clock_skew_seconds: int = 300,
        snapshot_reader: Callable[[str], ProviderSubscriptionSnapshot] | None = None,
    ) -> None:
        if not _PROVIDER_ID.fullmatch(provider_id):
            raise ValueError("INVALID_PROVIDER")
        if len(secret) < 16:
            raise ValueError("BILLING_PROVIDER_SECRET_TOO_SHORT")
        if max_clock_skew_seconds <= 0:
            raise ValueError("INVALID_PROVIDER_CLOCK_SKEW")
        self.provider_id = provider_id
        self._secret = bytes(secret)
        self._max_clock_skew_seconds = max_clock_skew_seconds
        self._snapshot_reader = snapshot_reader

    def verify_webhook(
        self,
        body: bytes,
        signature: str,
        *,
        now: datetime | None = None,
    ) -> VerifiedBillingWebhook:
        if not body or len(body) > 262_144:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID")
        timestamp, supplied = _parse_signature(signature)
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            raise ValueError("PROVIDER_VERIFIER_TIME_MUST_BE_AWARE")
        if abs(int(current.timestamp()) - timestamp) > self._max_clock_skew_seconds:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_STALE")
        expected = hmac.new(
            self._secret,
            str(timestamp).encode("ascii") + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
        try:
            raw = json.loads(body.decode("utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("PROVIDER_WEBHOOK_BODY_INVALID")
            payload = BillingWebhookRequest.model_validate(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_BODY_INVALID") from exc
        if payload.occurred_at.tzinfo is None:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_EVENT_TIME_INVALID")
        return VerifiedBillingWebhook(
            event_id=payload.event_id,
            provider=self.provider_id,
            provider_subscription_id=payload.provider_subscription_id,
            target_state=BillingState(payload.status),
            occurred_at=payload.occurred_at,
            external_reference=payload.external_reference,
            payload=dict(payload.payload),
            verification_method="hmac-sha256-v1",
            verified_at=current.astimezone(UTC),
        )

    def read_subscription(self, provider_subscription_id: str) -> ProviderSubscriptionSnapshot:
        if not provider_subscription_id or len(provider_subscription_id) > 256:
            raise ValueError("INVALID_PROVIDER_SUBSCRIPTION_ID")
        if self._snapshot_reader is None:
            raise RuntimeError("PROVIDER_RECONCILIATION_UNAVAILABLE")
        snapshot = self._snapshot_reader(provider_subscription_id)
        if snapshot.provider != self.provider_id:
            raise ValueError("PROVIDER_SNAPSHOT_MISMATCH")
        if snapshot.provider_subscription_id != provider_subscription_id:
            raise ValueError("PROVIDER_SNAPSHOT_MISMATCH")
        if snapshot.observed_at.tzinfo is None:
            raise ValueError("PROVIDER_SNAPSHOT_TIME_INVALID")
        if not snapshot.revision or len(snapshot.revision) > 256:
            raise ValueError("PROVIDER_SNAPSHOT_REVISION_INVALID")
        return snapshot


class BillingProviderRegistry:
    def __init__(self, adapters: tuple[BillingProviderAdapter, ...] = ()) -> None:
        self._adapters: dict[str, BillingProviderAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: BillingProviderAdapter) -> None:
        provider_id = adapter.provider_id
        if not _PROVIDER_ID.fullmatch(provider_id):
            raise ValueError("INVALID_PROVIDER")
        if provider_id in self._adapters:
            raise ValueError("BILLING_PROVIDER_ALREADY_REGISTERED")
        self._adapters[provider_id] = adapter

    def require(self, provider_id: str) -> BillingProviderAdapter:
        adapter = self._adapters.get(provider_id)
        if adapter is None:
            raise KeyError("BILLING_PROVIDER_NOT_CONFIGURED")
        return adapter

    def providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


def configured_provider_registry() -> BillingProviderRegistry:
    """Build the runtime registry from secret-free configuration references.

    The actual webhook secret is supplied only through the process environment.
    No provider credential or production network client is embedded in source.
    """

    provider = os.getenv("SENTINEL_BILLING_HMAC_PROVIDER", "").strip()
    secret = os.getenv("SENTINEL_BILLING_HMAC_WEBHOOK_SECRET", "")
    if not provider and not secret:
        return BillingProviderRegistry()
    if not provider or not secret:
        raise RuntimeError("BILLING_PROVIDER_NOT_CONFIGURED")
    adapter = HmacBillingProviderAdapter(provider, secret.encode("utf-8"))
    return BillingProviderRegistry((adapter,))


def _parse_signature(signature: str) -> tuple[int, str]:
    if not signature or len(signature) > 512:
        raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
    parts: dict[str, str] = {}
    for piece in signature.split(","):
        key, separator, value = piece.strip().partition("=")
        if not separator or key in parts:
            raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
        parts[key] = value
    if set(parts) != {"t", "v1"}:
        raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
    try:
        timestamp = int(parts["t"])
    except ValueError as exc:
        raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID") from exc
    digest = parts["v1"].lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_INVALID")
    return timestamp, digest
