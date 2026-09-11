from __future__ import annotations

import json
import socket
import ssl
import struct
from typing import Final

from .companion_protocol import CompanionEnvelope
from .companion_tls_peer import verify_certificate_fingerprint

_FRAME_HEADER: Final[int] = 4
_DEFAULT_MAX_FRAME_BYTES: Final[int] = 64 * 1024
_MAX_ALLOWED_FRAME_BYTES: Final[int] = 1024 * 1024


class CompanionTcpTransport:
    """Concrete length-prefixed TCP transport for Companion envelopes.

    The transport deliberately owns only byte transport. Authorization and
    action execution remain outside this boundary. For production use, callers
    must provide a TLS context; plaintext mode is available only when explicitly
    opted into for local/dev or test use.

    When ``pinned_peer_sha256`` is configured, the TLS peer certificate is
    additionally verified against that SHA-256 pin immediately after the TLS
    handshake. A mismatch closes the socket and fails closed before the
    transport becomes connected.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout_seconds: float = 5.0,
        ssl_context: ssl.SSLContext | None = None,
        allow_insecure: bool = False,
        max_frame_bytes: int = _DEFAULT_MAX_FRAME_BYTES,
        pinned_peer_sha256: str | None = None,
    ) -> None:
        if not host or len(host) > 255:
            raise ValueError("host must be between 1 and 255 characters")
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 1 <= max_frame_bytes <= _MAX_ALLOWED_FRAME_BYTES:
            raise ValueError("max_frame_bytes must be between 1 and 1048576")
        if ssl_context is None and not allow_insecure:
            raise ValueError("ssl_context is required unless allow_insecure=True")
        if pinned_peer_sha256 is not None and allow_insecure:
            raise ValueError("TLS peer pinning requires TLS; plaintext mode cannot provide a peer certificate")

        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.ssl_context = ssl_context
        self.max_frame_bytes = max_frame_bytes
        self.pinned_peer_sha256 = pinned_peer_sha256
        self._socket: socket.socket | None = None
        self.peer_certificate_sha256: str | None = None

    @property
    def connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        if self._socket is not None:
            return
        raw = socket.create_connection((self.host, self.port), timeout=self.timeout_seconds)
        raw.settimeout(self.timeout_seconds)
        try:
            if self.ssl_context is not None:
                wrapped = self.ssl_context.wrap_socket(raw, server_hostname=self.host)
                wrapped.settimeout(self.timeout_seconds)
                if self.pinned_peer_sha256 is not None:
                    certificate = wrapped.getpeercert(binary_form=True)
                    self.peer_certificate_sha256 = verify_certificate_fingerprint(
                        certificate,
                        self.pinned_peer_sha256,
                    )
                self._socket = wrapped
            else:
                self._socket = raw
        except (OSError, PermissionError, ValueError):
            raw.close()
            raise

    def send(self, envelope: CompanionEnvelope) -> None:
        payload = envelope.model_dump(mode="json")
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if len(body) > self.max_frame_bytes:
            raise ValueError("Companion envelope exceeds transport frame limit")
        sock = self._socket
        if sock is None:
            raise RuntimeError("transport is not connected")
        frame = struct.pack("!I", len(body)) + body
        try:
            sock.sendall(frame)
        except OSError:
            self.close()
            raise

    def close(self) -> None:
        sock, self._socket = self._socket, None
        self.peer_certificate_sha256 = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                sock.close()
