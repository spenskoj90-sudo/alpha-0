from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

import app.core.billing_provider_api as provider_api
from app.core.billing_provider import ProviderVerificationError
from app.main import app


class _ExplodingAdapter:
    provider_id = "signed-test"

    def verify_webhook(self, body: bytes, signature: str, *, now=None):
        del body, signature, now
        raise ProviderVerificationError(
            "Traceback: /srv/private/provider.py credential=must-never-reach-client"
        )


class _Registry:
    def require(self, provider: str):
        assert provider == "signed-test"
        return _ExplodingAdapter()


def test_provider_exception_text_is_never_reflected_to_webhook_client(monkeypatch) -> None:
    monkeypatch.setattr(provider_api, "configured_provider_registry", lambda: _Registry())
    client = TestClient(app)

    response = client.post(
        "/v1/billing/provider-webhooks/signed-test",
        content=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Billing-Signature": "opaque-signature",
        },
    )

    assert response.status_code == 401
    assert "PROVIDER_WEBHOOK_VERIFICATION_FAILED" in response.text
    assert "Traceback" not in response.text
    assert "/srv/private" not in response.text
    assert "credential=" not in response.text
