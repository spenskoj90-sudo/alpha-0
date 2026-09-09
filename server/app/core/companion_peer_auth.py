from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PeerAuthEvidence:
    """Evidence produced by a transport/security layer before authorization."""

    mechanism: str
    peer_id: str
    authenticated: bool

    def __post_init__(self) -> None:
        if not self.mechanism or len(self.mechanism) > 64:
            raise ValueError("mechanism must be between 1 and 64 characters")
        if not self.peer_id or len(self.peer_id) > 128:
            raise ValueError("peer_id must be between 1 and 128 characters")


@dataclass(frozen=True, slots=True)
class PeerAuthDecision:
    """Fail-closed decision separating authentication evidence from authorization."""

    accepted: bool
    peer_id: str | None
    reason_code: str


class CompanionPeerAuthenticator(Protocol):
    """Authenticate a peer from already-obtained transport evidence."""

    def authenticate(self, evidence: PeerAuthEvidence) -> PeerAuthDecision:
        ...


class AllowlistPeerAuthenticator:
    """Deterministic allowlist authorizer for local/test integration.

    This class does not prove possession of credentials or certificates. A
    production adapter must supply authenticated transport evidence first.
    """

    def __init__(self, allowed_peer_ids: set[str] | frozenset[str]) -> None:
        if not allowed_peer_ids:
            raise ValueError("allowed_peer_ids must not be empty")
        if any(not peer_id or len(peer_id) > 128 for peer_id in allowed_peer_ids):
            raise ValueError("peer IDs must be between 1 and 128 characters")
        self._allowed_peer_ids = frozenset(allowed_peer_ids)

    def authenticate(self, evidence: PeerAuthEvidence) -> PeerAuthDecision:
        if not evidence.authenticated:
            return PeerAuthDecision(
                accepted=False,
                peer_id=None,
                reason_code="PEER_NOT_AUTHENTICATED",
            )
        if evidence.peer_id not in self._allowed_peer_ids:
            return PeerAuthDecision(
                accepted=False,
                peer_id=None,
                reason_code="PEER_NOT_AUTHORIZED",
            )
        return PeerAuthDecision(
            accepted=True,
            peer_id=evidence.peer_id,
            reason_code="PEER_AUTHORIZED",
        )
