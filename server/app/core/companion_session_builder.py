from __future__ import annotations

from dataclasses import dataclass

from .companion_peer_auth import CompanionPeerAuthenticator
from .companion_runtime import CompanionRuntime, CompanionRuntimeConfig
from .companion_runtime_builder import build_companion_runtime
from .companion_transport import CompanionTransportSession


@dataclass(frozen=True, slots=True)
class CompanionSessionBundle:
    runtime: CompanionRuntime
    session: CompanionTransportSession


def build_companion_session(
    *,
    config: CompanionRuntimeConfig | None = None,
    peer_authenticator: CompanionPeerAuthenticator | None = None,
) -> CompanionSessionBundle:
    """Build one transport-neutral Companion runtime/session composition."""
    runtime = build_companion_runtime(config=config)
    session = CompanionTransportSession(
        runtime,
        peer_authenticator=peer_authenticator,
    )
    return CompanionSessionBundle(runtime=runtime, session=session)
