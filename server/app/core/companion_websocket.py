from __future__ import annotations

import base64
import ipaddress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from .billing_provider_api import router as billing_provider_router
from .companion_compatibility import negotiate_companion_compatibility
from .companion_peer_auth import (
    AllowlistPeerAuthenticator,
    CompanionPeerAuthenticator,
    PeerAuthEvidence,
)
from .companion_protocol import (
    CompanionEnvelope,
    CompanionHandshake,
    CompanionHandshakeResult,
    CompanionMode,
    CompanionQueue,
)
from .companion_runtime import CompanionRuntime
from .companion_runtime_builder import build_companion_runtime
from .companion_transport import CompanionTransportSession

router = APIRouter(tags=["companion"])
router.include_router(billing_provider_router)

_PUBLIC_SUBPROTOCOL = "sentinel.v1"
_AUTH_SUBPROTOCOL_PREFIX = "sentinel.auth."
_MAX_SESSION_TOKEN_LENGTH = 4096


@dataclass(frozen=True, slots=True)
class CompanionTransportCompatibility:
    ugs_schema_version: str = "1.0"
    adapter_contract_version: str = "1.0"
    core_protocol_version: str = "1.0"
    capability_profile: str = "wow.passive.v1"
    supported_protocols: tuple[str, ...] = ("1.0",)
    supported_ugs_schemas: tuple[str, ...] = ("1.0",)
    supported_adapter_contracts: tuple[str, ...] = ("1.0",)
    supported_core_protocols: tuple[str, ...] = ("1.0",)
    supported_capability_profiles: tuple[str, ...] = ("wow.passive.v1",)


def is_loopback_peer(host: str | None) -> bool:
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def offered_subprotocols(websocket: WebSocket) -> tuple[str, ...]:
    raw = websocket.headers.get("sec-websocket-protocol", "")
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def authorization_from_subprotocol(websocket: WebSocket) -> str | None:
    """Recover an opaque bearer token without putting it in the WebSocket URL.

    Browser-compatible WebSocket clients cannot set arbitrary Authorization
    headers. The launcher therefore sends a base64url-encoded opaque session
    token as a non-selected auth subprotocol. The server selects only the public
    `sentinel.v1` protocol and never echoes the auth-bearing protocol back.
    """

    for protocol in offered_subprotocols(websocket):
        if not protocol.startswith(_AUTH_SUBPROTOCOL_PREFIX):
            continue
        encoded = protocol.removeprefix(_AUTH_SUBPROTOCOL_PREFIX)
        if not encoded or len(encoded) > 5500:
            return None
        try:
            padding = "=" * ((4 - len(encoded) % 4) % 4)
            token = base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
        if not token or len(token) > _MAX_SESSION_TOKEN_LENGTH:
            return None
        return f"Bearer {token}"
    return None


class CompanionWebSocketTransport:
    """Concrete loopback WebSocket transport over the authenticated session seam."""

    def __init__(
        self,
        websocket: WebSocket,
        *,
        compatibility: CompanionTransportCompatibility | None = None,
        runtime: CompanionRuntime | None = None,
        queue: CompanionQueue | None = None,
        peer_authenticator: CompanionPeerAuthenticator | None = None,
        peer_auth_evidence_factory: Callable[[str], PeerAuthEvidence] | None = None,
    ) -> None:
        self.websocket = websocket
        self.compatibility = compatibility or CompanionTransportCompatibility()
        self.peer_authenticator = peer_authenticator
        self.peer_auth_evidence_factory = peer_auth_evidence_factory or (
            lambda host: PeerAuthEvidence(
                mechanism="loopback",
                peer_id=host,
                authenticated=True,
            )
        )
        self.session = CompanionTransportSession(
            runtime or build_companion_runtime(),
            queue,
            peer_authenticator,
        )
        self._handshaken = False
        self._closed = False

    @property
    def health(self):
        return self.session.health()

    async def accept(self) -> bool:
        host = self.websocket.client.host if self.websocket.client else None
        if not is_loopback_peer(host):
            await self.websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="LOOPBACK_ONLY")
            self._closed = True
            return False
        assert host is not None
        if self.peer_authenticator is None:
            self.peer_authenticator = AllowlistPeerAuthenticator({host})
            self.session.peer_authenticator = self.peer_authenticator
        try:
            self.session.connect(auth_evidence=self.peer_auth_evidence_factory(host))
        except (PermissionError, ValueError):
            await self.websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="PEER_AUTHORIZATION_FAILED",
            )
            self._closed = True
            return False
        selected = _PUBLIC_SUBPROTOCOL if _PUBLIC_SUBPROTOCOL in offered_subprotocols(self.websocket) else None
        await self.websocket.accept(subprotocol=selected)
        return True

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

        compatibility = negotiate_companion_compatibility(
            offered_protocol=offered.protocol_version,
            supported_protocols=self.compatibility.supported_protocols,
            offered_ugs_schema=offered.ugs_schema_version,
            supported_ugs_schemas=self.compatibility.supported_ugs_schemas,
            offered_adapter_contract=offered.adapter_contract_version,
            supported_adapter_contracts=self.compatibility.supported_adapter_contracts,
            offered_core_protocol=offered.core_protocol_version,
            supported_core_protocols=self.compatibility.supported_core_protocols,
            offered_capability_profile=offered.capability_profile,
            supported_capability_profiles=self.compatibility.supported_capability_profiles,
        )
        if compatibility.accepted:
            reason_code = "HANDSHAKE_ACCEPTED"
        elif compatibility.reason_code == "CAPABILITY_PROFILE_UNSUPPORTED":
            reason_code = "CAPABILITY_PROFILE_MISMATCH"
        else:
            negotiated_dimensions = (
                (offered.protocol_version, self.compatibility.supported_protocols, "PROTOCOL_VERSION_UNSUPPORTED"),
                (offered.ugs_schema_version, self.compatibility.supported_ugs_schemas, "UGS_SCHEMA_MISMATCH"),
                (offered.adapter_contract_version, self.compatibility.supported_adapter_contracts, "ADAPTER_CONTRACT_MISMATCH"),
                (offered.core_protocol_version, self.compatibility.supported_core_protocols, "CORE_PROTOCOL_MISMATCH"),
            )
            reason_code = next(
                (
                    reason
                    for offered_version, supported, reason in negotiated_dimensions
                    if not _has_compatible_version(offered_version, supported)
                ),
                "VERSION_NEGOTIATION_FAILED",
            )
        result = CompanionHandshakeResult(
            accepted=compatibility.accepted,
            reason_code=reason_code,
            mode=CompanionMode.ACTIVE if compatibility.accepted else CompanionMode.STOPPED,
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
            self._closed = True
            self.session.close()
            await self.websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="INVALID_ENVELOPE")
            return None
        if not self.session.enqueue(envelope):
            return None
        return envelope

    async def send(self) -> CompanionEnvelope | None:
        """Send exactly one queued envelope and measure local transport-call latency."""
        if self._closed or not self._handshaken:
            return None
        queued = self.session.queue.peek()
        if queued is None:
            return None
        sent_at = datetime.now(UTC)
        try:
            await self.websocket.send_json(queued.model_dump(mode="json"))
        except Exception:
            self.session.mark_transport_failure()
            return None
        received_at = datetime.now(UTC)
        self.session.runtime.observe_latency(sent_at, received_at)
        return self.session.mark_send_success(received_at)

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


def _has_compatible_version(offered: str, supported: tuple[str, ...]) -> bool:
    try:
        from .companion_compatibility import negotiate_version

        return negotiate_version(offered, supported) is not None
    except ValueError:
        return False


async def _authorize_companion_account(websocket: WebSocket) -> bool:
    """Bind Companion activation to a Core session and paid feature grant."""

    authorization = websocket.headers.get("authorization") or authorization_from_subprotocol(websocket)
    if not authorization:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="AUTHENTICATION_REQUIRED",
        )
        return False
    from app.main import billing_service, principal_from_token, require_bearer, store

    try:
        principal = principal_from_token(require_bearer(authorization))
    except HTTPException:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="INVALID_SESSION",
        )
        return False
    if not billing_service.has_feature(principal.user_id, "companion"):
        store.add_audit({
            "actor_user_id": principal.user_id,
            "actor_device_id": principal.device_id,
            "action": "companion:connect",
            "resource": "companion",
            "decision": "DENY",
            "reason_code": "COMPANION_ENTITLEMENT_REQUIRED",
            "request_id": None,
        })
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="COMPANION_ENTITLEMENT_REQUIRED",
        )
        return False
    store.add_audit({
        "actor_user_id": principal.user_id,
        "actor_device_id": principal.device_id,
        "action": "companion:connect",
        "resource": "companion",
        "decision": "ALLOW",
        "reason_code": "COMPANION_ENTITLEMENT_ACTIVE",
        "request_id": None,
    })
    return True


@router.websocket("/v1/companion/ws")
async def companion_websocket(websocket: WebSocket) -> None:
    # Network locality is checked before account state so remote peers cannot
    # use this endpoint as an account/session oracle.
    host = websocket.client.host if websocket.client else None
    if not is_loopback_peer(host):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="LOOPBACK_ONLY")
        return
    if not await _authorize_companion_account(websocket):
        return
    transport = CompanionWebSocketTransport(websocket)
    if not await transport.accept():
        return
    try:
        result = await transport.handshake()
        if not result.accepted:
            return
        while True:
            envelope = await transport.receive_envelope()
            if envelope is None:
                return
    except WebSocketDisconnect:
        return
    finally:
        transport._fail_transport()
