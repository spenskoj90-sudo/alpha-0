from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.companion_protocol import CompanionEnvelope, CompanionHandshake, CompanionMessageType, LatencyClass
from app.core.companion_websocket import CompanionTransportCompatibility, is_loopback_peer
from app.main import app


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


def test_loopback_policy_accepts_ip_addresses_only() -> None:
    assert is_loopback_peer("127.0.0.1") is True
    assert is_loopback_peer("::1") is True
    assert is_loopback_peer("192.0.2.1") is False
    assert is_loopback_peer("localhost") is False
    assert is_loopback_peer(None) is False


def test_websocket_rejects_non_loopback_peer_before_runtime_activation() -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with non_loopback_client.websocket_connect("/v1/companion/ws"):
            pass
    assert exc.value.code == 1008


def test_websocket_handshake_is_real_socket_level_integration() -> None:
    with client.websocket_connect("/v1/companion/ws") as websocket:
        websocket.send_json(handshake())
        result = websocket.receive_json()

        assert result == {
            "accepted": True,
            "reason_code": "HANDSHAKE_ACCEPTED",
            "mode": "ACTIVE",
        }

        websocket.send_json(envelope())


def test_websocket_handshake_rejects_incompatible_profile_fail_closed() -> None:
    with client.websocket_connect("/v1/companion/ws") as websocket:
        websocket.send_json(handshake(capability_profile="unknown.profile"))
        result = websocket.receive_json()

        assert result["accepted"] is False
        assert result["reason_code"] == "CAPABILITY_PROFILE_MISMATCH"
        assert result["mode"] == "STOPPED"

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_websocket_rejects_malformed_envelope_after_handshake() -> None:
    with client.websocket_connect("/v1/companion/ws") as websocket:
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
