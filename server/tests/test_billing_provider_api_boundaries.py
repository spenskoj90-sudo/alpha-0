from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from app import main as main_module
import app.core.billing_provider_api as provider_api
from app.core.billing_provider import ProviderEventIgnored, ProviderVerificationError
from app.core.stripe_billing import StripeProviderError
from app.main import app


client = TestClient(app)


def _session_headers() -> dict[str, str]:
    suffix = uuid.uuid4().hex
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"billing-boundary-{suffix}@example.com",
            "password": f"Correct-Horse-Battery-Staple-{suffix}",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['session_token']}"}


class _CheckoutAdapter:
    def __init__(self, *, error: Exception | None = None, prices: dict[str, str] | None = None) -> None:
        self.config = SimpleNamespace(price_ids=prices if prices is not None else {"core-plus": "price_test"})
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def create_checkout_session(self, subscription_id: str, plan_code: str):
        self.calls.append((subscription_id, plan_code))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            session_id="cs_test_boundary",
            checkout_url="https://checkout.stripe.com/c/pay/cs_test_boundary",
            livemode=False,
        )


@pytest.mark.parametrize(
    ("plan_code", "status", "detail"),
    [
        ("missing-plan", 400, "UNKNOWN_PLAN"),
        ("core", 400, "FREE_PLAN_REQUIRES_NO_CHECKOUT"),
    ],
)
def test_checkout_rejects_unknown_and_free_plans_before_provider_use(monkeypatch, plan_code, status, detail) -> None:
    monkeypatch.setattr(main_module, "rate_limit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        provider_api,
        "configured_stripe_adapter",
        lambda: (_ for _ in ()).throw(AssertionError("provider must not be consulted")),
    )
    response = client.post(
        "/v1/billing/checkout-sessions",
        headers=_session_headers(),
        json={"plan_code": plan_code},
    )
    assert response.status_code == status
    assert response.json()["code"] == detail


@pytest.mark.parametrize("mode", ["none", "runtime", "value", "missing-price"])
def test_checkout_fails_closed_for_incomplete_stripe_configuration(monkeypatch, mode: str) -> None:
    monkeypatch.setattr(main_module, "rate_limit", lambda *_args, **_kwargs: None)
    if mode == "none":
        monkeypatch.setattr(provider_api, "configured_stripe_adapter", lambda: None)
        expected = "STRIPE_NOT_CONFIGURED"
    elif mode == "runtime":
        monkeypatch.setattr(
            provider_api,
            "configured_stripe_adapter",
            lambda: (_ for _ in ()).throw(RuntimeError("internal secret detail")),
        )
        expected = "STRIPE_NOT_CONFIGURED"
    elif mode == "value":
        monkeypatch.setattr(
            provider_api,
            "configured_stripe_adapter",
            lambda: (_ for _ in ()).throw(ValueError("internal config detail")),
        )
        expected = "STRIPE_NOT_CONFIGURED"
    else:
        monkeypatch.setattr(
            provider_api,
            "configured_stripe_adapter",
            lambda: _CheckoutAdapter(prices={}),
        )
        expected = "STRIPE_PLAN_NOT_CONFIGURED"

    response = client.post(
        "/v1/billing/checkout-sessions",
        headers=_session_headers(),
        json={"plan_code": "core-plus"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == expected
    assert "internal" not in response.text


def test_checkout_reuses_pending_row_and_maps_provider_failure_without_entitlement(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "rate_limit", lambda *_args, **_kwargs: None)
    headers = _session_headers()
    adapter = _CheckoutAdapter()
    monkeypatch.setattr(provider_api, "configured_stripe_adapter", lambda: adapter)

    first = client.post(
        "/v1/billing/checkout-sessions",
        headers=headers,
        json={"plan_code": "core-plus"},
    )
    second = client.post(
        "/v1/billing/checkout-sessions",
        headers=headers,
        json={"plan_code": "core-plus"},
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["subscription_id"] == second.json()["subscription_id"]
    assert adapter.calls[0][0] == adapter.calls[1][0]

    failing = _CheckoutAdapter(error=StripeProviderError("STRIPE_API_UNAVAILABLE"))
    monkeypatch.setattr(provider_api, "configured_stripe_adapter", lambda: failing)
    failed = client.post(
        "/v1/billing/checkout-sessions",
        headers=headers,
        json={"plan_code": "core-plus"},
    )
    assert failed.status_code == 502
    assert failed.json()["code"] == "STRIPE_API_UNAVAILABLE"

    features = client.get("/v1/billing/features", headers=headers)
    assert features.status_code == 200
    assert features.json()["features"] == []


class _WebhookAdapter:
    def __init__(self, outcome) -> None:
        self.outcome = outcome

    def verify_webhook(self, body: bytes, signature: str):
        assert body
        assert signature
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class _Registry:
    def __init__(self, adapter=None, error: BaseException | None = None) -> None:
        self.adapter = adapter
        self.error = error

    def require(self, provider: str):
        if self.error is not None:
            raise self.error
        assert provider in {"signed-test", "stripe"}
        return self.adapter


def _post_webhook(provider: str, *, body: bytes = b"{}", signature: bool = True):
    headers = {"Content-Type": "application/json"}
    if signature:
        headers["Stripe-Signature" if provider == "stripe" else "X-Billing-Signature"] = "opaque"
    return client.post(f"/v1/billing/provider-webhooks/{provider}", content=body, headers=headers)


def test_verified_webhook_validates_provider_configuration_signature_and_size(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "rate_limit", lambda *_args, **_kwargs: None)

    bad_provider = _post_webhook("bad!")
    assert bad_provider.status_code == 400
    assert bad_provider.json()["code"] == "INVALID_PROVIDER"

    for error in (KeyError("missing"), RuntimeError("missing"), ValueError("missing")):
        monkeypatch.setattr(provider_api, "configured_provider_registry", lambda error=error: _Registry(error=error))
        response = _post_webhook("signed-test")
        assert response.status_code == 503
        assert response.json()["code"] == "BILLING_PROVIDER_NOT_CONFIGURED"

    monkeypatch.setattr(provider_api, "configured_provider_registry", lambda: _Registry(_WebhookAdapter(SimpleNamespace())))
    assert _post_webhook("signed-test", signature=False).json()["code"] == "PROVIDER_WEBHOOK_SIGNATURE_REQUIRED"
    assert _post_webhook("stripe", signature=False).json()["code"] == "PROVIDER_WEBHOOK_SIGNATURE_REQUIRED"

    oversized = _post_webhook("signed-test", body=b"x" * 262_145)
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "PROVIDER_WEBHOOK_BODY_TOO_LARGE"


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (ProviderEventIgnored("STRIPE_EVENT_IGNORED"), 200, "STRIPE_EVENT_IGNORED"),
        (ProviderEventIgnored("private provider reason"), 200, "PROVIDER_EVENT_IGNORED"),
        (ProviderVerificationError("PROVIDER_WEBHOOK_SIGNATURE_STALE"), 401, "PROVIDER_WEBHOOK_SIGNATURE_STALE"),
        (ProviderVerificationError("private verifier path"), 401, "PROVIDER_WEBHOOK_VERIFICATION_FAILED"),
        (ValueError("private parser detail"), 400, "PROVIDER_WEBHOOK_INVALID"),
    ],
)
def test_verified_webhook_maps_adapter_failures_to_bounded_public_codes(monkeypatch, error, status, detail) -> None:
    monkeypatch.setattr(main_module, "rate_limit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        provider_api,
        "configured_provider_registry",
        lambda: _Registry(_WebhookAdapter(error)),
    )
    response = _post_webhook("signed-test")
    assert response.status_code == status
    if status == 200:
        assert response.json() == {"accepted": False, "ignored": True, "reason": detail}
    else:
        assert response.json()["code"] == detail
    assert "private" not in response.text


@pytest.mark.parametrize(
    ("billing_error", "status", "detail"),
    [
        ("SUBSCRIPTION_NOT_FOUND", 404, "SUBSCRIPTION_NOT_FOUND"),
        ("SUBSCRIPTION_STATE_CHANGED", 409, "SUBSCRIPTION_STATE_CHANGED"),
        ("SUBSCRIPTION_PROVIDER_MISMATCH", 409, "SUBSCRIPTION_PROVIDER_MISMATCH"),
        ("INVALID_BILLING_TRANSITION:ACTIVE:CANCELED", 409, "INVALID_BILLING_TRANSITION"),
        ("internal database detail", 400, "BILLING_WEBHOOK_INVALID"),
    ],
)
def test_verified_webhook_maps_billing_conflicts_without_internal_text(monkeypatch, billing_error, status, detail) -> None:
    monkeypatch.setattr(main_module, "rate_limit", lambda *_args, **_kwargs: None)
    verified = SimpleNamespace(verification_method="test-signature-v1")
    monkeypatch.setattr(
        provider_api,
        "configured_provider_registry",
        lambda: _Registry(_WebhookAdapter(verified)),
    )

    class _Billing:
        def apply_verified_webhook(self, _verified):
            raise ValueError(billing_error)

    monkeypatch.setattr(main_module, "billing_service", _Billing())
    response = _post_webhook("signed-test")
    assert response.status_code == status
    assert response.json()["code"] == detail
    assert "database" not in response.text
