from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status

from .companion_protocol import (
    CompanionEnvelope,
    CompanionHandshake,
    CompanionHandshakeResult,
    CompanionMode,
    CompanionQueue,
    negotiate_handshake,
)
from .companion_runtime import CompanionRuntime
from .companion_transport import CompanionTransportSession


@dataclass(frozen=True, slots=True)
class CompanionTransportCompatibility:
    ugs_schema_version: str = "1.0"
    adapter_contract_version: str = "1.0"
    core_protocol_version: str = "1.0"
    capability_profile: str = "wow.passive.v1"


def is_loopback_peer(host: str | None) -> bool:
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class CompanionWebSocketTransport:
    """Concrete loopback WebSocket transport over the existing Companion session seam."""

    def __init__(
        self,
        websocket: WebSocket,
        *,
        compatibility: CompanionTransportCompatibility | None = None,
        runtime: CompanionRuntime | None = None,
        queue: CompanionQueue | None = None,
    ) -> None:
        self.websocket = websocket
        self.compatibility = compatibility or CompanionTransportCompatibility()
        self.session = CompanionTransportSession(runtime or CompanionRuntime(), queue)
        self._handshaken = False
        self._closed = False

    @property
    def health(self):
        return self.session.health()

    async def accept(self) -> None:
        host = self.websocket.client.host if self.websocket.client else None
        if not is_loopback_peer(host):
            await self.websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="LOOPBACK_ONLY")
            self._closed = True
            return
        await self.websocket.accept()
        self.session.connect()

    async def handshake(self) -> CompanionHandshakeResult:
        if self._closed:
            raise RuntimeError("transport is closed")
        try:
            raw: Any = await self.websocket.receive_json()
            offered = CompanionHandshake.model_validate(raw)
        except WebSocketDisconnect:
            self._fail_transport()
            raise
        except Exception:
            self._closed = True
            self.session.close()
            await self.websocket.close(code=status.WS_1002_PROTOCOL_ERROR, reason="INVALID_HANDSHAKE")
            return CompanionHandshakeResult(
                accepted=False,
                reason_code="INVALID_HANDSHAKE",
                mode=CompanionMode.STOPPED,
            )

        result = negotiate_handshake(
            offered,
            expected_ugs_schema=self.compatibility.ugs_schema_version,
            expected_adapter_contract=self.compatibility.adapter_contract_version,
            expected_core_protocol=self.compatibility.core_protocol_version,
            expected_capability_profile=self.compatibility.capability_profile,
        )
        await self.websocket.send_json(result.model_dump(mode="json"))
        if not result.accepted:
            self._closed = True
            self.session.close()
            await self.websocket.close(code=status.WS_1002_PROTOCOL_ERROR, reason=result.reason_code)
            return result
        self._handshaken = True
        return result

    async def receive_envelope(self) -> CompanionEnvelope | None:
        if self._closed or not self._handshaken:
            return None
        try:
            raw: Any = await self.websocket.receive_json()
            envelope = CompanionEnvelope.model_validate(raw)
        except WebSocketDisconnect:
            self._fail_transport()
            raise
        except Exception:
            await self.websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="INVALID_ENVELOPE")
            self._closed = True
            self.session.close()
            return None
        if not self.session.enqueue(envelope):
            return None
        return envelope

    async def send(self) -> CompanionEnvelope | None:
        if self._closed or not self._handshaken:
            return None
        queued = self.session.queue.pop()
        if queued is None:
            return None
        try:
            await self.websocket.send_json(queued.model_dump(mode="json"))
        except Exception:
            self.session.mark_transport_failure()
            return None
        self.session.last_successful_send = self.session.runtime._utc(None)
        return queued

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.session.close()
        try:
            await self.websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except RuntimeError:
            pass

    def _fail_transport(self) -> None:
        if not self._closed:
            self.session.mark_transport_failure()
            self._closed = True


def install_companion_websocket_route(
    app: FastAPI,
    *,
    compatibility: CompanionTransportCompatibility | None = None,
) -> None:
    """Install the loopback-only Companion WebSocket endpoint."""

    @app.websocket("/v1/companion/ws")
    async def companion_websocket(websocket: WebSocket) -> None:
        transport = CompanionWebSocketTransport(websocket, compatibility=compatibility)
        await transport.accept()
        if transport.health.mode is CompanionMode.STOPPED:
            return
        result = await transport.handshake()
        if not result.accepted:
            return
        try:
            while True:
                await transport.receive_envelope()
        except WebSocketDisconnect:
            return
        finally:
            transport._fail_transport()
