from __future__ import annotations

import ssl

from .companion_peer_auth import CompanionPeerAuthenticator
from .companion_runtime_builder import build_companion_runtime
from .companion_runtime import CompanionRuntimeConfig
from .companion_tcp_transport import CompanionTcpTransport
from .companion_transport import CompanionTransportSession
from .companion_transport_binding import CompanionTransportBinding


def build_companion_tcp_session(
    host: str,
    port: int,
    *,
    config: CompanionRuntimeConfig | None = None,
    peer_authenticator: CompanionPeerAuthenticator | None = None,
    ssl_context: ssl.SSLContext | None = None,
    allow_insecure: bool = False,
    max_frame_bytes: int = 64 * 1024,
    persistent_engine=None,
) -> tuple[CompanionTransportSession, CompanionTcpTransport]:
    """Construct the TCP transport and session without opening a connection.

    TLS remains mandatory by default. Peer authentication is injected into the
    session and is evaluated before runtime activation when ``connect`` is
    called. Network I/O is deliberately deferred to the caller. Persistence
    is explicit through ``persistent_engine`` and is never created implicitly.
    """
    runtime = build_companion_runtime(
        config=config,
        persistent_engine=persistent_engine,
    )
    session = CompanionTransportSession(
        runtime,
        peer_authenticator=peer_authenticator,
    )
    transport = CompanionTcpTransport(
        host,
        port,
        ssl_context=ssl_context,
        allow_insecure=allow_insecure,
        max_frame_bytes=max_frame_bytes,
    )
    return session, transport


def build_companion_tcp_binding(
    host: str,
    port: int,
    *,
    config: CompanionRuntimeConfig | None = None,
    peer_authenticator: CompanionPeerAuthenticator | None = None,
    ssl_context: ssl.SSLContext | None = None,
    allow_insecure: bool = False,
    max_frame_bytes: int = 64 * 1024,
    persistent_engine=None,
) -> CompanionTransportBinding:
    """Construct a TCP transport bound to the Companion security/session seam.

    Construction performs no network I/O. The returned binding evaluates peer
    authorization before opening the TCP connection and preserves the existing
    TLS-by-default transport policy. Persistent telemetry is opt-in and uses
    the same explicit engine boundary as the runtime builder.
    """
    session, transport = build_companion_tcp_session(
        host,
        port,
        config=config,
        peer_authenticator=peer_authenticator,
        ssl_context=ssl_context,
        allow_insecure=allow_insecure,
        max_frame_bytes=max_frame_bytes,
        persistent_engine=persistent_engine,
    )
    return CompanionTransportBinding(session, transport)
