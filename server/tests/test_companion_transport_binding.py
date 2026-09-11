from datetime import datetime, timezone

import pytest

from app.core.companion_peer_auth import AllowlistPeerAuthenticator, PeerAuthEvidence
from app.core.companion_protocol import CompanionEnvelope, CompanionMessageType, LatencyClass, CompanionQueue
from app.core.companion_runtime import CompanionRuntime
from app.core.companion_transport import CompanionTransportSession
from app.core.companion_transport_binding import CompanionTransportBinding


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def envelope(sequence: int) -> CompanionEnvelope:
    return CompanionEnvelope(
        sequence=sequence,
        message_type=CompanionMessageType.HEARTBEAT,
        latency_class=LatencyClass.RESPONSIVE,
    )


class FakeTransport:
    def __init__(self) -> None:
        self.connected = False
        self.sent: list[CompanionEnvelope] = []
        self.closed = False
        self.fail_send = False

    def connect(self) -> None:
        self.connected = True

    def send(self, value: CompanionEnvelope) -> None:
        if not self.connected:
            raise RuntimeError("not connected")
        if self.fail_send:
            raise OSError("send failed")
        self.sent.append(value)

    def close(self) -> None:
        self.closed = True
        self.connected = False


def test_denied_peer_never_opens_network_transport() -> None:
    transport = FakeTransport()
    session = CompanionTransportSession(
        CompanionRuntime(),
        peer_authenticator=AllowlistPeerAuthenticator({"peer-a"}),
    )
    binding = CompanionTransportBinding(session, transport)

    with pytest.raises(PermissionError, match="PEER_NOT_AUTHORIZED"):
        binding.connect(
            BASE,
            auth_evidence=PeerAuthEvidence(
                mechanism="test",
                peer_id="peer-b",
                authenticated=True,
            ),
        )

    assert transport.connected is False


def test_authorized_peer_connects_transport_after_session_authorization() -> None:
    transport = FakeTransport()
    session = CompanionTransportSession(
        CompanionRuntime(),
        CompanionQueue(max_items=2),
        AllowlistPeerAuthenticator({"peer-a"}),
    )
    binding = CompanionTransportBinding(session, transport)

    binding.connect(
        BASE,
        auth_evidence=PeerAuthEvidence(
            mechanism="test",
            peer_id="peer-a",
            authenticated=True,
        ),
    )

    assert transport.connected is True
    assert session.health().peer_id == "peer-a"


def test_send_next_preserves_fifo_and_records_completion_evidence() -> None:
    transport = FakeTransport()
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=2))
    binding = CompanionTransportBinding(session, transport)
    binding.connect(BASE)
    first = envelope(1)
    second = envelope(2)
    session.enqueue(first)
    session.enqueue(second)

    evidence = binding.send_next(BASE)

    assert evidence is not None
    assert evidence.elapsed_ms >= 0
    assert evidence.completed_at == BASE
    assert transport.sent == [first]
    assert session.queue.peek() == second


def test_kill_switch_prevents_bound_transport_send() -> None:
    transport = FakeTransport()
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=2))
    binding = CompanionTransportBinding(session, transport)
    binding.connect(BASE)
    session.enqueue(envelope(1))
    session.activate_kill_switch()

    assert binding.send_next(BASE) is None
    assert transport.sent == []
    assert session.queue.depth == 0


def test_transport_send_failure_degrades_session_and_preserves_queued_item() -> None:
    transport = FakeTransport()
    transport.fail_send = True
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=2))
    binding = CompanionTransportBinding(session, transport)
    binding.connect(BASE)
    queued = envelope(1)
    session.enqueue(queued)

    with pytest.raises(OSError, match="send failed"):
        binding.send_next(BASE)

    assert session.health().mode.name == "DEGRADED"
    assert session.queue.peek() == queued


def test_close_closes_both_transport_and_session() -> None:
    transport = FakeTransport()
    session = CompanionTransportSession(CompanionRuntime())
    binding = CompanionTransportBinding(session, transport)
    binding.connect(BASE)

    binding.close()

    assert transport.closed is True
    assert session.health().mode.name == "STOPPED"
