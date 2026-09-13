from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.billing import BillingWebhookEvent
from app.core.companion_protocol import CompanionEnvelope, CompanionMessageType, LatencyClass
from app.core.p1_runtime import BillingState
from app.main import app, billing_service, principal_from_token, store


client = TestClient(app, client=("127.0.0.1", 43125))


def _handshake() -> dict[str, str]:
    return {
        "protocol_version": "1.0",
        "ugs_schema_version": "1.0",
        "adapter_contract_version": "1.0",
        "core_protocol_version": "1.0",
        "capability_profile": "wow.passive.v1",
    }


def _entitled_session() -> tuple[str, str]:
    suffix = uuid.uuid4().hex
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"wow-checkpoint-{suffix}@example.com",
            "password": f"Correct-Horse-Battery-Staple-{suffix}",
        },
    )
    assert response.status_code == 200
    token = response.json()["session_token"]
    principal = principal_from_token(token)
    assert "game:write" not in principal.scopes
    provider_subscription_id = f"wow-checkpoint-{suffix}"
    billing_service.create_subscription(
        principal.user_id,
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
    return token, principal.user_id


def _observation(event_id: str = "wow-checkpoint-test", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": event_id,
        "observed_at": datetime.now(UTC).isoformat(),
        "sequence": 7,
        "patch_profile": "wotlk-3.3.5a",
        "server_profile": "unknown",
        "realm_id": "Example Realm",
        "latency_ms": 84,
        "addon_connected": True,
        "launcher_associated": False,
        "account_entitled": False,
        "combat_state": "IDLE",
        "data_quality": "LOW",
        "provenance": ["sentinel-addon-savedvariables", "sentinel-launcher-checkpoint"],
    }
    payload.update(overrides)
    return payload


def _envelope(payload: dict[str, object], sequence: int = 1) -> dict[str, object]:
    return CompanionEnvelope(
        sequence=sequence,
        message_type=CompanionMessageType.WOW_OBSERVATION,
        latency_class=LatencyClass.BACKGROUND,
        payload=payload,
    ).model_dump(mode="json")


def test_passive_wow_checkpoint_is_normalized_and_acknowledged_without_game_write_scope() -> None:
    token, user_id = _entitled_session()
    with client.websocket_connect(
        "/v1/companion/ws",
        headers={"Authorization": f"Bearer {token}"},
    ) as websocket:
        websocket.send_json(_handshake())
        assert websocket.receive_json()["accepted"] is True
        websocket.send_json(_envelope(_observation()))
        ack = websocket.receive_json()

    assert ack["message_type"] == "WOW_OBSERVATION_ACK"
    assert ack["latency_class"] == "BACKGROUND"
    assert ack["payload"] == {
        "event_id": "wow-checkpoint-test",
        "accepted": True,
        "reason": "PASSIVE_CHECKPOINT_ACCEPTED",
    }
    audits = store.get_audit(user_id)
    assert any(
        item.get("action") == "companion:wow-observation"
        and item.get("request_id") == "wow-checkpoint-test"
        and item.get("decision") == "ALLOW"
        for item in audits
    )


def test_invalid_wow_checkpoint_is_rejected_without_terminating_companion_session() -> None:
    token, _ = _entitled_session()
    with client.websocket_connect(
        "/v1/companion/ws",
        headers={"Authorization": f"Bearer {token}"},
    ) as websocket:
        websocket.send_json(_handshake())
        assert websocket.receive_json()["accepted"] is True

        websocket.send_json(_envelope(_observation("invalid-event", patch_profile="unsupported"), 1))
        rejected = websocket.receive_json()
        assert rejected["message_type"] == "WOW_OBSERVATION_ACK"
        assert rejected["payload"] == {
            "event_id": "invalid-event",
            "accepted": False,
            "reason": "INVALID_WOW_OBSERVATION",
        }

        websocket.send_json(_envelope(_observation("valid-after-reject"), 2))
        accepted = websocket.receive_json()
        assert accepted["payload"]["event_id"] == "valid-after-reject"
        assert accepted["payload"]["accepted"] is True
