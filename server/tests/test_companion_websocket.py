from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.billing import BillingWebhookEvent
from app.core.companion_protocol import CompanionEnvelope, CompanionHandshake, CompanionMessageType, LatencyClass
from app.core.companion_websocket import CompanionTransportCompatibility, is_loopback_peer
from app.core.p1_runtime import BillingState
from app.main import app, billing_service, principal_from_token


client = TestClient(app, client=("127.0.0.1", 43123))
non_loopback_client = TestClient(app, client=("192.0.2.1", 43124))


def handshake(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "protocol_version": "1.0",
        "ugs_schema_version": "1.0",
        "adapter_contract_version": "1.0",
        "core_protocol_version": "1.0",
        "capability_profile": "wow.passive.v1",
    }
    values.update(overrides)
    return values


def envelope(sequence: int = 1) -> dict[str, object]:
    return CompanionEnvelope(
        sequence=sequence,
        message_type=CompanionMessageType.HEARTBEAT,
        latency_class=LatencyClass.RESPONSIVE,
    ).model_dump(mode="json")


def _registered_session() -> tuple[str, str]:
    suffix = uuid.uuid4().hex
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"companion-{suffix}@example.com",
            "password": f"Correct-Horse-Battery-Staple-{suffix}",
        },
    )
    assert response.status_code == 200
    token = response.json()["session_token"]
    return token, principal_from_token(token).user_id


def entitled_headers() -> dict[str, str]:
    token, user_id = _registered_session()
    provider_subscription_id = f"ws-{uuid.uuid4().hex}"
    billing_service.create_subscription(
        user_id,
        "core-plus",
        provider="test",
        provider_subscription_id=provider_subscription_id,
    )
    billing_service.apply_webhook(
        BillingWebhookEvent(
            event_id=f"evt-{uuid.uuid4().hex}",
            provider="test",
            provider_subscription_id=provider_subscription_id,
            target_state=BillingState.ACTIVE,
            occurred_at=datetime.now(UTC),
        )
    )
    return {"Authorization": f"Bearer {token}"}


def unentitled_headers() -> dict[str, str]:
    token, _ = _registered_session()
    return {"Authorization": f"Bearer {token}"}


def test_loopback_policy_accepts_ip_addresses_only() -> None:
    assert is_loopback_peer("127.0.0.1") is True
    assert is_loopback_peer("::1") is True
    assert is_loopback_peer("192.0.2.1") is False
    assert is_loopback_peer("localhost") is False
    assert is_loopback_peer(None) is False


def test_websocket_rejects_non_loopback_peer_before_account_or_runtime_activation() -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with non_loopback_client.websocket_connect("/v1/companion/ws"):
            pass
    assert exc.value.code == 1008


def test_websocket_rejects_unauthenticated_loopback_account() -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/v1/companion/ws"):
            pass
    assert exc.value.code == 1008


def test_websocket_rejects_authenticated_account_without_companion_entitlement() -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/v1/companion/ws", headers=unentitled_headers()):
            pass
    assert exc.value.code == 1008


def test_websocket_handshake_and_heartbeat_health_are_real_socket_level_integration() -> None:
    with client.websocket_connect("/v1/companion/ws", headers=entitled_headers()) as websocket:
        websocket.send_json(handshake())
        result = websocket.receive_json()

        assert result == {
            "accepted": True,
            "reason_code": "HANDSHAKE_ACCEPTED",
            "mode": "ACTIVE",
        }

        heartbeat = envelope()
        websocket.send_json(heartbeat)
        health = websocket.receive_json()

        assert health["sequence"] == heartbeat["sequence"]
        assert health["message_type"] == "HEALTH"
        assert health["latency_class"] == "RESPONSIVE"
        assert health["payload"]["health_kind"] == "runtime"
        assert health["payload"]["heartbeat_message_id"] == heartbeat["message_id"]
        assert uuid.UUID(health["payload"]["connection_id"])
        assert health["payload"]["mode"] == "ACTIVE"
        assert health["payload"]["peer_authenticated"] is True
        assert health["payload"]["queue_depth"] == 0
        assert "peer_id" not in health["payload"]
        assert "authorization" not in health["payload"]


def test_websocket_handshake_rejects_incompatible_profile_fail_closed() -> None:
    with client.websocket_connect("/v1/companion/ws", headers=entitled_headers()) as websocket:
        websocket.send_json(handshake(capability_profile="unknown.profile"))
        result = websocket.receive_json()

        assert result["accepted"] is False
        assert result["reason_code"] == "CAPABILITY_PROFILE_MISMATCH"
        assert result["mode"] == "STOPPED"

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_websocket_rejects_malformed_envelope_after_handshake() -> None:
    with client.websocket_connect("/v1/companion/ws", headers=entitled_headers()) as websocket:
        websocket.send_json(handshake())
        assert websocket.receive_json()["accepted"] is True
        websocket.send_json({"sequence": "not-an-int", "message_type": "HEARTBEAT"})

        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 1003


def test_handshake_contract_matches_current_reference_profile() -> None:
    offered = CompanionHandshake.model_validate(handshake())
    expected = CompanionTransportCompatibility()

    assert offered.ugs_schema_version == expected.ugs_schema_version
    assert offered.adapter_contract_version == expected.adapter_contract_version
    assert offered.core_protocol_version == expected.core_protocol_version
    assert offered.capability_profile == expected.capability_profile
