import json
import socket
import struct
import threading
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.core.companion_peer_auth import AllowlistPeerAuthenticator, PeerAuthEvidence
from app.core.companion_protocol import CompanionEnvelope, CompanionMessageType, LatencyClass, CompanionQueue
from app.core.companion_runtime import CompanionRuntime
from app.core.companion_tcp_transport import CompanionTcpTransport
from app.core.companion_transport import CompanionTransportSession
from app.core.companion_transport_binding import CompanionTransportBinding


def envelope() -> CompanionEnvelope:
    return CompanionEnvelope(
        sequence=7,
        message_type=CompanionMessageType.HEARTBEAT,
        latency_class=LatencyClass.RESPONSIVE,
        payload={"source": "test"},
    )


def start_receiver() -> tuple[int, list[bytes], threading.Event, threading.Thread]:
    ready = threading.Event()
    received: list[bytes] = []
    port_box: list[int] = []

    def serve() -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(2)
            port_box.append(listener.getsockname()[1])
            ready.set()
            conn, _ = listener.accept()
            with conn:
                header = conn.recv(4)
                size = struct.unpack("!I", header)[0]
                data = b""
                while len(data) < size:
                    chunk = conn.recv(size - len(data))
                    if not chunk:
                        break
                    data += chunk
                received.append(data)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    assert ready.wait(2)
    return port_box[0], received, ready, thread


def test_transport_requires_explicit_tls_or_insecure_opt_in() -> None:
    with pytest.raises(ValueError, match="ssl_context"):
        CompanionTcpTransport("127.0.0.1", 1)


def test_tcp_transport_sends_length_prefixed_json_frame() -> None:
    port, received, _, thread = start_receiver()
    transport = CompanionTcpTransport("127.0.0.1", port, allow_insecure=True)

    transport.connect()
    transport.send(envelope())
    transport.close()
    thread.join(timeout=2)

    assert len(received) == 1
    decoded = json.loads(received[0])
    assert decoded["sequence"] == 7
    assert decoded["message_type"] == "HEARTBEAT"
    assert decoded["payload"] == {"source": "test"}


def test_bound_session_delivers_through_real_loopback_tcp() -> None:
    port, received, _, thread = start_receiver()
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=2))
    transport = CompanionTcpTransport("127.0.0.1", port, allow_insecure=True)
    binding = CompanionTransportBinding(session, transport)
    binding.connect(datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert binding.session.enqueue(envelope()) is True

    evidence = binding.send_next(datetime(2026, 1, 1, tzinfo=timezone.utc))
    binding.close()
    thread.join(timeout=2)

    assert evidence is not None
    assert evidence.elapsed_ms >= 0
    assert len(received) == 1
    assert json.loads(received[0])["sequence"] == 7
    assert session.health().queue_depth == 0


def test_bound_session_rejects_unauthorized_peer_before_loopback_connect() -> None:
    transport = CompanionTcpTransport("127.0.0.1", 1, allow_insecure=True)
    session = CompanionTransportSession(
        CompanionRuntime(),
        peer_authenticator=AllowlistPeerAuthenticator({"peer-allowed"}),
    )
    binding = CompanionTransportBinding(session, transport)

    with pytest.raises(PermissionError, match="PEER_NOT_AUTHORIZED"):
        binding.connect(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            auth_evidence=PeerAuthEvidence(
                mechanism="test",
                peer_id="peer-denied",
                authenticated=True,
            ),
        )

    assert transport.connected is False


def test_send_requires_connection() -> None:
    transport = CompanionTcpTransport("127.0.0.1", 1, allow_insecure=True)

    with pytest.raises(RuntimeError, match="not connected"):
        transport.send(envelope())


def test_frame_limit_is_enforced_before_socket_write() -> None:
    transport = CompanionTcpTransport("127.0.0.1", 1, allow_insecure=True, max_frame_bytes=32)
    fake_socket = Mock(spec=socket.socket)
    transport._socket = fake_socket

    with pytest.raises(ValueError, match="frame limit"):
        transport.send(envelope())

    fake_socket.sendall.assert_not_called()


def test_frame_limit_cannot_exceed_one_megabyte() -> None:
    with pytest.raises(ValueError, match="1048576"):
        CompanionTcpTransport("127.0.0.1", 1, allow_insecure=True, max_frame_bytes=1024 * 1024 + 1)


def test_close_is_idempotent() -> None:
    transport = CompanionTcpTransport("127.0.0.1", 1, allow_insecure=True)
    transport.close()
    transport.close()
    assert transport.connected is False
