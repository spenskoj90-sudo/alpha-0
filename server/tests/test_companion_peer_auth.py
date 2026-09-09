import pytest

from app.core.companion_peer_auth import (
    AllowlistPeerAuthenticator,
    PeerAuthDecision,
    PeerAuthEvidence,
)


def test_peer_auth_requires_authenticated_evidence() -> None:
    authenticator = AllowlistPeerAuthenticator({"companion-test"})

    decision = authenticator.authenticate(
        PeerAuthEvidence(
            mechanism="test-evidence",
            peer_id="companion-test",
            authenticated=False,
        )
    )

    assert decision == PeerAuthDecision(
        accepted=False,
        peer_id=None,
        reason_code="PEER_NOT_AUTHENTICATED",
    )


def test_peer_auth_fail_closed_for_unknown_peer() -> None:
    authenticator = AllowlistPeerAuthenticator({"companion-test"})

    decision = authenticator.authenticate(
        PeerAuthEvidence(
            mechanism="test-evidence",
            peer_id="unknown-peer",
            authenticated=True,
        )
    )

    assert decision.accepted is False
    assert decision.peer_id is None
    assert decision.reason_code == "PEER_NOT_AUTHORIZED"


def test_peer_auth_accepts_known_authenticated_peer() -> None:
    authenticator = AllowlistPeerAuthenticator({"companion-test"})

    decision = authenticator.authenticate(
        PeerAuthEvidence(
            mechanism="test-evidence",
            peer_id="companion-test",
            authenticated=True,
        )
    )

    assert decision.accepted is True
    assert decision.peer_id == "companion-test"
    assert decision.reason_code == "PEER_AUTHORIZED"


def test_peer_auth_rejects_empty_allowlist_and_invalid_evidence() -> None:
    with pytest.raises(ValueError, match="allowed_peer_ids"):
        AllowlistPeerAuthenticator(set())

    with pytest.raises(ValueError, match="mechanism"):
        PeerAuthEvidence(mechanism="", peer_id="peer", authenticated=True)
