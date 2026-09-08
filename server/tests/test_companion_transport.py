from datetime import datetime, timedelta, timezone

import pytest

from app.core.companion_protocol import CompanionEnvelope, CompanionMessageType, CompanionQueue, LatencyClass, CompanionMode
from app.core.companion_runtime import CompanionRuntime
from app.core.companion_transport import CompanionTransportSession


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def envelope(sequence: int) -> CompanionEnvelope:
    return CompanionEnvelope(
        sequence=sequence,
        message_type=CompanionMessageType.HEARTBEAT,
        latency_class=LatencyClass.RESPONSIVE,
    )


def test_connect_and_health_expose_runtime_and_queue_state() -> None:
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=2))

    session.connect(BASE)
    session.enqueue(envelope(1))
    session.enqueue(envelope(2))
    health = session.health()

    assert health.mode is CompanionMode.ACTIVE
    assert health.queue_depth == 2
    assert health.dropped_events == 0
    assert health.last_heartbeat == BASE
    assert health.last_successful_send is None
    assert health.kill_switch_active is False


def test_successful_send_consumes_fifo_and_records_timestamp() -> None:
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=2))
    session.connect(BASE)
    first = envelope(1)
    second = envelope(2)
    session.enqueue(first)
    session.enqueue(second)

    sent = session.mark_send_success(BASE + timedelta(milliseconds=50))

    assert sent == first
    assert session.health().queue_depth == 1
    assert session.health().last_successful_send == BASE + timedelta(milliseconds=50)
    assert session.queue.pop() == second


def test_queue_peek_is_non_destructive_until_send_is_acknowledged() -> None:
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=2))
    session.connect(BASE)
    first = envelope(1)
    session.enqueue(first)

    assert session.queue.peek() == first
    assert session.health().queue_depth == 1
    assert session.queue.peek() == first

    assert session.mark_send_success(BASE) == first
    assert session.health().queue_depth == 0


def test_transport_failure_degrades_but_does_not_stop_session() -> None:
    session = CompanionTransportSession(CompanionRuntime())
    session.connect(BASE)

    mode = session.mark_transport_failure(BASE + timedelta(seconds=1))

    assert mode is CompanionMode.DEGRADED
    assert session.health().mode is CompanionMode.DEGRADED


def test_reconnect_attempts_use_runtime_backoff() -> None:
    runtime = CompanionRuntime()
    session = CompanionTransportSession(runtime)
    session.connect(BASE)
    session.mark_transport_failure(BASE)

    assert session.register_reconnect_attempt() == timedelta(seconds=1)
    assert session.register_reconnect_attempt() == timedelta(seconds=2)
    assert session.health().reconnect_attempts == 2


def test_queue_overflow_is_visible_in_health() -> None:
    session = CompanionTransportSession(CompanionRuntime(), CompanionQueue(max_items=1))
    session.connect(BASE)
    session.enqueue(envelope(1))
    session.enqueue(envelope(2))

    health = session.health()

    assert health.queue_depth == 1
    assert health.dropped_events == 1
    assert session.queue.pop().sequence == 2


def test_closed_session_is_fail_closed() -> None:
    session = CompanionTransportSession(CompanionRuntime())
    session.connect(BASE)
    session.close()

    assert session.enqueue(envelope(1)) is False
    assert session.mark_send_success(BASE) is None
    assert session.health().mode is CompanionMode.STOPPED
    with pytest.raises(RuntimeError, match="closed"):
        session.register_reconnect_attempt()


def test_kill_switch_stops_session_and_blocks_reconnect() -> None:
    session = CompanionTransportSession(CompanionRuntime())
    session.connect(BASE)
    session.enqueue(envelope(1))

    session.activate_kill_switch()

    health = session.health()
    assert health.mode is CompanionMode.STOPPED
    assert health.kill_switch_active is True
    assert health.queue_depth == 0
    assert session.enqueue(envelope(2)) is False
    assert session.mark_send_success(BASE) is None
    with pytest.raises(RuntimeError, match="kill switch"):
        session.register_reconnect_attempt()


def test_kill_switch_reset_requires_fresh_connect() -> None:
    session = CompanionTransportSession(CompanionRuntime())
    session.connect(BASE)
    session.activate_kill_switch()
    session.reset_kill_switch()

    health = session.health()
    assert health.mode is CompanionMode.STOPPED
    assert health.kill_switch_active is False
    assert session.enqueue(envelope(1)) is True

    session.connect(BASE + timedelta(seconds=1))
    assert session.health().mode is CompanionMode.ACTIVE
