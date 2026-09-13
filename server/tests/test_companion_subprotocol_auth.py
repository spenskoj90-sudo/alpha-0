from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.billing import BillingWebhookEvent
from app.core.p1_runtime import BillingState
from app.main import app, billing_service, principal_from_token


client = TestClient(app, client=("127.0.0.1", 43125))


def _entitled_token() -> str:
    suffix = uuid.uuid4().hex
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"launcher-{suffix}@example.com",
            "password": f"Correct-Horse-Battery-Staple-{suffix}",
        },
    )
    assert response.status_code == 200
    token = response.json()["session_token"]
    user_id = principal_from_token(token).user_id
    provider_subscription_id = f"launcher-{suffix}"
    billing_service.create_subscription(
        user_id,
        "core-plus",
        provider="test",
        provider_subscription_id=provider_subscription_id,
    )
    billing_service.apply_webhook(
        BillingWebhookEvent(
            event_id=f"evt-{suffix}",
            provider="test",
            provider_subscription_id=provider_subscription_id,
            target_state=BillingState.ACTIVE,
            occurred_at=datetime.now(UTC),
        )
    )
    return token


def _auth_protocol(token: str) -> str:
    encoded = base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii").rstrip("=")
    return f"sentinel.auth.{encoded}"


def _handshake() -> dict[str, str]:
    return {
        "protocol_version": "1.0",
        "ugs_schema_version": "1.0",
        "adapter_contract_version": "1.0",
        "core_protocol_version": "1.0",
        "capability_profile": "wow.passive.v1",
    }


def test_launcher_browser_compatible_auth_subprotocol_is_accepted_without_bearer_header() -> None:
    token = _entitled_token()
    with client.websocket_connect(
        "/v1/companion/ws",
        subprotocols=["sentinel.v1", _auth_protocol(token)],
    ) as websocket:
        assert websocket.accepted_subprotocol == "sentinel.v1"
        websocket.send_json(_handshake())
        result = websocket.receive_json()
        assert result["accepted"] is True
        assert result["mode"] == "ACTIVE"


def test_auth_subprotocol_is_not_selected_or_echoed() -> None:
    token = _entitled_token()
    secret_protocol = _auth_protocol(token)
    with client.websocket_connect(
        "/v1/companion/ws",
        subprotocols=["sentinel.v1", secret_protocol],
    ) as websocket:
        assert websocket.accepted_subprotocol == "sentinel.v1"
        assert websocket.accepted_subprotocol != secret_protocol
        websocket.send_json(_handshake())
        assert websocket.receive_json()["accepted"] is True


def test_malformed_auth_subprotocol_fails_closed() -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/v1/companion/ws",
            subprotocols=["sentinel.v1", "sentinel.auth.not-base64-***"],
        ):
            pass
    assert exc.value.code == 1008
