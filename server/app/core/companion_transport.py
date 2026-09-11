from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from .companion_peer_auth import (
    CompanionPeerAuthenticator,
    PeerAuthDecision,
    PeerAuthEvidence,
)
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
    peer_authenticated: bool
    peer_id: str | None


class CompanionTransportSession:
    """Binds protocol queue, peer authorization, runtime health and transport telemetry."""

    def __init__(
        self,
        runtime: CompanionRuntime,
        queue: CompanionQueue | None = None,
        peer_authenticator: CompanionPeerAuthenticator | None = None,
    ) -> None:
        self.runtime = runtime
        self.queue = queue or CompanionQueue()
        self.peer_authenticator = peer_authenticator
        self.peer_auth_decision: PeerAuthDecision | None = None
        self.last_successful_send: datetime | None = None
        self._closed = False

    def connect(
        self,
        now: datetime | None = None,
        *,
        auth_evidence: PeerAuthEvidence | None = None,
    ) -> PeerAuthDecision | None:
        if self._closed:
            raise RuntimeError("transport session is closed")
        if self.peer_authenticator is not None:
            if auth_evidence is None:
                self.peer_auth_decision = PeerAuthDecision(
                    accepted=False,
                    peer_id=None,
                    reason_code="PEER_AUTHENTICATION_REQUIRED",
                )
                self.runtime.record_transport_event(
                    "companion.transport.connect.denied",
                    reason="PEER_AUTHENTICATION_REQUIRED",
                )
                raise PermissionError("PEER_AUTHENTICATION_REQUIRED")
            decision = self.peer_authenticator.authenticate(auth_evidence)
            self.peer_auth_decision = decision
            if not decision.accepted:
                self.runtime.record_transport_event(
                    "companion.transport.connect.denied",
                    reason=decision.reason_code,
                )
                raise PermissionError(decision.reason_code)
        self.runtime.start(now)
        self.runtime.record_transport_event(
            "companion.transport.connected",
            peer_authenticated=self.peer_auth_decision.accepted if self.peer_auth_decision else False,
        )
        return self.peer_auth_decision

    def enqueue(self, envelope: CompanionEnvelope) -> bool:
        if self._closed or self.runtime.kill_switch.active:
            return False
        accepted = self.queue.push(envelope)
        if not accepted:
            self.runtime.record_transport_event("companion.transport.queue.rejected")
        elif self.queue.dropped:
            self.runtime.record_transport_event(
                "companion.transport.queue.dropped",
                dropped_events=self.queue.dropped,
            )
        return accepted

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
        timestamp = self.runtime.timestamp_utc(now)
        self.last_successful_send = timestamp
        self.runtime.record_transport_event("companion.transport.send.success", timestamp)

    def mark_transport_failure(self, now: datetime | None = None) -> CompanionMode:
        """Make transport loss visible as degradation and emit bounded telemetry."""
        if self._closed:
            return CompanionMode.STOPPED
        self.runtime.degrade()
        self.runtime.record_transport_event("companion.transport.failure", now)
        return self.runtime.mode

    def register_reconnect_attempt(self) -> timedelta:
        if self._closed:
            raise RuntimeError("transport session is closed")
        delay = self.runtime.register_reconnect_attempt()
        self.runtime.record_transport_event(
            "companion.transport.reconnect.scheduled",
            delay_ms=delay.total_seconds() * 1000,
            attempt=self.runtime.reconnect_attempts,
        )
        return delay

    def activate_kill_switch(self) -> None:
        """Stop locally and prevent queue admission or reconnect until explicit reset."""
        self.runtime.activate_kill_switch()
        self.runtime.record_transport_event("companion.transport.kill_switch")
        self.queue.stop()

    def reset_kill_switch(self) -> None:
        """Clear the local latch; a fresh connect is still required before sending."""
        if self._closed:
            raise RuntimeError("transport session is closed")
        self.runtime.reset_kill_switch()
        self.peer_auth_decision = None
        self.queue.reset()
        self.runtime.record_transport_event("companion.transport.kill_switch.reset")

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
            peer_authenticated=(
                self.peer_auth_decision is not None and self.peer_auth_decision.accepted
            ),
            peer_id=(
                self.peer_auth_decision.peer_id
                if self.peer_auth_decision is not None
                else None
            ),
        )

    def close(self) -> None:
        self._closed = True
        self.queue.stop()
        self.runtime.stop()
        self.runtime.record_transport_event("companion.transport.closed")
