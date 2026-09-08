from __future__ import annotations

from collections import deque
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class CompanionMessageType(StrEnum):
    HANDSHAKE = "HANDSHAKE"
    HANDSHAKE_ACK = "HANDSHAKE_ACK"
    UGS_UPDATE = "UGS_UPDATE"
    HEARTBEAT = "HEARTBEAT"
    HEALTH = "HEALTH"
    SHUTDOWN = "SHUTDOWN"


class CompanionMode(StrEnum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    STOPPED = "STOPPED"


class LatencyClass(StrEnum):
    INTERACTIVE = "INTERACTIVE"
    RESPONSIVE = "RESPONSIVE"
    BACKGROUND = "BACKGROUND"


class CompanionHandshake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str = Field(pattern=r"^1\.\d+$", max_length=16)
    ugs_schema_version: str = Field(pattern=r"^1\.\d+$", max_length=16)
    adapter_contract_version: str = Field(pattern=r"^1\.\d+$", max_length=16)
    core_protocol_version: str = Field(pattern=r"^1\.\d+$", max_length=16)
    capability_profile: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    instance_id: UUID = Field(default_factory=uuid4)


class CompanionHandshakeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    reason_code: str
    mode: CompanionMode


class CompanionEnvelope(BaseModel):
    """Transport-neutral bounded protocol envelope; it is not a command executor."""

    model_config = ConfigDict(extra="forbid")

    message_id: UUID = Field(default_factory=uuid4)
    sequence: int = Field(ge=0, le=2**63 - 1)
    message_type: CompanionMessageType
    latency_class: LatencyClass
    payload: dict[str, object] = Field(default_factory=dict, max_length=64)


class CompanionQueue:
    """Bounded FIFO queue with explicit backpressure and stop semantics."""

    def __init__(self, max_items: int = 128) -> None:
        if not 1 <= max_items <= 4096:
            raise ValueError("max_items must be between 1 and 4096")
        self._items: deque[CompanionEnvelope] = deque(maxlen=max_items)
        self._max_items = max_items
        self._dropped = 0
        self._stopped = False

    @property
    def max_items(self) -> int:
        return self._max_items

    @property
    def depth(self) -> int:
        return len(self._items)

    @property
    def dropped(self) -> int:
        return self._dropped

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self) -> None:
        self._stopped = True
        self._items.clear()

    def reset(self) -> None:
        """Explicitly reopen the queue after a local kill-switch reset."""
        self._items.clear()
        self._stopped = False

    def push(self, envelope: CompanionEnvelope) -> bool:
        if self._stopped:
            return False
        if len(self._items) >= self._max_items:
            self._items.popleft()
            self._dropped += 1
        self._items.append(envelope)
        return True

    def peek(self) -> CompanionEnvelope | None:
        if not self._items:
            return None
        return self._items[0]

    def pop(self) -> CompanionEnvelope | None:
        if not self._items:
            return None
        return self._items.popleft()


def negotiate_handshake(
    offered: CompanionHandshake,
    *,
    expected_ugs_schema: str,
    expected_adapter_contract: str,
    expected_core_protocol: str,
    expected_capability_profile: str,
) -> CompanionHandshakeResult:
    """Accept only exact v1 compatibility for the first protocol slice."""

    if offered.protocol_version != "1.0":
        return CompanionHandshakeResult(
            accepted=False,
            reason_code="PROTOCOL_VERSION_UNSUPPORTED",
            mode=CompanionMode.STOPPED,
        )
    if offered.ugs_schema_version != expected_ugs_schema:
        return CompanionHandshakeResult(
            accepted=False,
            reason_code="UGS_SCHEMA_MISMATCH",
            mode=CompanionMode.STOPPED,
        )
    if offered.adapter_contract_version != expected_adapter_contract:
        return CompanionHandshakeResult(
            accepted=False,
            reason_code="ADAPTER_CONTRACT_MISMATCH",
            mode=CompanionMode.STOPPED,
        )
    if offered.core_protocol_version != expected_core_protocol:
        return CompanionHandshakeResult(
            accepted=False,
            reason_code="CORE_PROTOCOL_MISMATCH",
            mode=CompanionMode.STOPPED,
        )
    if offered.capability_profile != expected_capability_profile:
        return CompanionHandshakeResult(
            accepted=False,
            reason_code="CAPABILITY_PROFILE_MISMATCH",
            mode=CompanionMode.STOPPED,
        )
    return CompanionHandshakeResult(
        accepted=True,
        reason_code="HANDSHAKE_ACCEPTED",
        mode=CompanionMode.ACTIVE,
    )


def latency_class_for_budget(budget_ms: int) -> LatencyClass:
    if budget_ms < 0:
        raise ValueError("budget_ms must be non-negative")
    if budget_ms <= 250:
        return LatencyClass.INTERACTIVE
    if budget_ms <= 1000:
        return LatencyClass.RESPONSIVE
    return LatencyClass.BACKGROUND
