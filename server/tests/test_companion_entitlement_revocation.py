from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.billing import BillingWebhookEvent
from app.core.companion_protocol import CompanionEnvelope, CompanionMessageType, LatencyClass
from app.core.p1_runtime import BillingState
from app.main import app, billing_service, principal_from_token


client = TestClient(app, client=("127.0.0.1", 43126))


def _active_subscription() -> tuple[str, str]:
    suffix = uuid.uuid4().hex
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"revoke-{suffix}@example.com",
            "password": f"Correct-Horse-Battery-Staple-{suffix}",
        },
    )
    assert response.status_code == 200
    token = response.json()["session_token"]
    user_id = principal_from_token(token).user_id
    provider_subscription_id = f"revoke-{suffix}"
    billing_service.create_subscription(
        user_id,
        "core-plus",
        provider="test",
        provider_subscription_id=provider_subscription_id,
    )
    billing_service.apply_webhook(
        BillingWebhookEvent(
            event_id=f"active-{suffix}",
            provider="test",
            provider_subscription_id=provider_subscription_id,
            target_state=BillingState.ACTIVE,
            occurred_at=datetime.now(UTC),
        )
    )
    return token, provider_subscription_id


def test_live_companion_session_is_revoked_when_subscription_leaves_active_state() -> None:
    token, provider_subscription_id = _active_subscription()
    with client.websocket_connect(
        "/v1/companion/ws",
        headers={"Authorization": f"Bearer {token}"},
    ) as websocket:
        websocket.send_json({
            "protocol_version": "1.0",
            "ugs_schema_version": "1.0",
            "adapter_contract_version": "1.0",
            "core_protocol_version": "1.0",
            "capability_profile": "wow.passive.v1",
        })
        assert websocket.receive_json()["accepted"] is True

        billing_service.apply_webhook(
            BillingWebhookEvent(
                event_id=f"past-due-{uuid.uuid4().hex}",
                provider="test",
                provider_subscription_id=provider_subscription_id,
                target_state=BillingState.PAST_DUE,
                occurred_at=datetime.now(UTC),
            )
        )
        websocket.send_json(
            CompanionEnvelope(
                sequence=1,
                message_type=CompanionMessageType.HEARTBEAT,
                latency_class=LatencyClass.RESPONSIVE,
            ).model_dump(mode="json")
        )
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 1008
        assert exc.value.reason == "COMPANION_ENTITLEMENT_REVOKED"
