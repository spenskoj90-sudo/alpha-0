from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from .companion_protocol import CompanionEnvelope, CompanionMode, CompanionQueue
from .companion_runtime import CompanionRuntime


class CompanionTransport(Protocol):
    """Minimal synchronous transport seam for bounded Companion delivery."""

    def send(self, envelope: CompanionEnvelope) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class CompanionRuntimeHealth:
    mode: CompanionMode
    last_heartbeat: datetime | None
    last_latency_ms: float | None
    reconnect_attempts: int
    queue_depth: int
    dropped_events: int
    last_successful_send: datetime | None
    kill_switch_active: bool


class CompanionTransportSession:
    """Binds protocol queue state to runtime health without choosing network I/O."""

    def __init__(self, runtime: CompanionRuntime, queue: CompanionQueue | None = None) -> None:
        self.runtime = runtime
        self.queue = queue or CompanionQueue()
        self.last_successful_send: datetime | None = None
        self._closed = False

    def connect(self, now: datetime | None = None) -> None:
        if self._closed:
            raise RuntimeError("transport session is closed")
        self.runtime.start(now)

    def enqueue(self, envelope: CompanionEnvelope) -> bool:
        if self._closed or self.runtime.kill_switch.active:
            return False
        return self.queue.push(envelope)

    def mark_send_success(self, now: datetime | None = None) -> CompanionEnvelope | None:
        """Record a successful transport send and consume exactly one queued envelope."""
        if self._closed or self.runtime.kill_switch.active:
            return None
        sent = self.queue.pop()
        if sent is None:
            return None
        self.record_send_success(now)
        return sent

    def record_send_success(self, now: datetime | None = None) -> None:
        """Record transport-level send completion without changing queue state."""
        if self._closed or self.runtime.kill_switch.active:
            return
        self.last_successful_send = self.runtime.timestamp_utc(now)

    def mark_transport_failure(self, now: datetime | None = None) -> CompanionMode:
        """Make transport loss visible as degradation; never authorize or execute actions."""
        if self._closed:
            return CompanionMode.STOPPED
        self.runtime.degrade()
        return self.runtime.mode

    def register_reconnect_attempt(self) -> timedelta:
        if self._closed:
            raise RuntimeError("transport session is closed")
        return self.runtime.register_reconnect_attempt()

    def activate_kill_switch(self) -> None:
        """Stop locally and prevent queue admission or reconnect until explicit reset."""
        self.runtime.activate_kill_switch()
        self.queue.stop()

    def reset_kill_switch(self) -> None:
        """Clear the local latch; a fresh connect is still required before sending."""
        if self._closed:
            raise RuntimeError("transport session is closed")
        self.runtime.reset_kill_switch()
        self.queue = CompanionQueue(max_items=self.queue.max_items)

    def health(self) -> CompanionRuntimeHealth:
        return CompanionRuntimeHealth(
            mode=self.runtime.mode,
            last_heartbeat=self.runtime.last_heartbeat,
            last_latency_ms=self.runtime.last_latency_ms,
            reconnect_attempts=self.runtime.reconnect_attempts,
            queue_depth=self.queue.depth,
            dropped_events=self.queue.dropped,
            last_successful_send=self.last_successful_send,
            kill_switch_active=self.runtime.kill_switch.active,
        )

    def close(self) -> None:
        self._closed = True
        self.queue.stop()
        self.runtime.stop()
