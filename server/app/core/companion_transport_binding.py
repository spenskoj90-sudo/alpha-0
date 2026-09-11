from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from typing import Protocol

from .companion_peer_auth import PeerAuthEvidence
from .companion_protocol import CompanionEnvelope
from .companion_transport import CompanionTransport, CompanionTransportSession


class ConnectableCompanionTransport(CompanionTransport, Protocol):
    def connect(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class TransportSendEvidence:
    """Local transport timing evidence for one successful send."""

    elapsed_ms: float
    completed_at: datetime

    def __post_init__(self) -> None:
        if self.elapsed_ms < 0:
            raise ValueError("elapsed_ms cannot be negative")


class CompanionTransportBinding:
    """Bind a transport to the existing authorized Companion session.

    Authentication is evaluated by the session before the network transport is
    connected. The binding performs no authorization itself and never enables
    action execution. Transport timing is local evidence only.
    """

    def __init__(
        self,
        session: CompanionTransportSession,
        transport: ConnectableCompanionTransport,
    ) -> None:
        self.session = session
        self.transport = transport

    def connect(
        self,
        now: datetime | None = None,
        *,
        auth_evidence: PeerAuthEvidence | None = None,
    ) -> None:
        # Establish the Companion security decision before opening the network
        # socket. A denied peer therefore cannot cause transport connection.
        self.session.connect(now, auth_evidence=auth_evidence)
        try:
            self.transport.connect()
        except Exception:
            self.session.mark_transport_failure(now)
            raise

    def send_next(self, now: datetime | None = None) -> TransportSendEvidence | None:
        """Send exactly one queued envelope and record local elapsed time."""
        if self.session.runtime.kill_switch.active:
            return None
        envelope: CompanionEnvelope | None = self.session.queue.peek()
        if envelope is None:
            return None
        started = monotonic()
        try:
            self.transport.send(envelope)
        except Exception:
            self.session.mark_transport_failure(now)
            raise
        elapsed_ms = (monotonic() - started) * 1000.0
        sent = self.session.mark_send_success(now)
        if sent is None:
            return None
        return TransportSendEvidence(
            elapsed_ms=elapsed_ms,
            completed_at=self.session.runtime.timestamp_utc(now),
        )

    def close(self) -> None:
        try:
            self.transport.close()
        finally:
            self.session.close()
