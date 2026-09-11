import ssl

from app.core.companion_peer_auth import AllowlistPeerAuthenticator
from app.core.companion_tcp_session import build_companion_tcp_session


def test_tcp_session_factory_defers_network_io_and_injects_auth() -> None:
    authenticator = AllowlistPeerAuthenticator({"peer-1"})
    session, transport = build_companion_tcp_session(
        "127.0.0.1",
        65535,
        peer_authenticator=authenticator,
        allow_insecure=True,
    )
    assert session.peer_authenticator is authenticator
    assert transport.connected is False


def test_tcp_session_factory_preserves_tls_requirement_by_default() -> None:
    try:
        build_companion_tcp_session("127.0.0.1", 65535)
    except ValueError as exc:
        assert "ssl_context" in str(exc)
    else:
        raise AssertionError("TLS should be required unless insecure mode is explicit")
