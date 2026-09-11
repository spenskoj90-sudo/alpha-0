from app.core.companion_peer_auth import AllowlistPeerAuthenticator
from app.core.companion_runtime import CompanionRuntimeConfig
from app.core.companion_session_builder import build_companion_session


def test_session_builder_composes_runtime_and_session():
    bundle = build_companion_session(config=CompanionRuntimeConfig())
    assert bundle.session.runtime is bundle.runtime
    assert bundle.runtime.telemetry is not None
    assert bundle.session.peer_authenticator is None


def test_session_builder_preserves_peer_authenticator():
    authenticator = AllowlistPeerAuthenticator({"peer-a"})
    bundle = build_companion_session(peer_authenticator=authenticator)
    assert bundle.session.peer_authenticator is authenticator
