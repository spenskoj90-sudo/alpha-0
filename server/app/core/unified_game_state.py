from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.game_adapter import (
    AdapterEvent,
    CapabilityStatus,
    DataQuality,
    EvidenceLevel,
)


class CombatState(StrEnum):
    UNKNOWN = "UNKNOWN"
    OUT_OF_COMBAT = "OUT_OF_COMBAT"
    IN_COMBAT = "IN_COMBAT"


class ObservationKind(StrEnum):
    OBSERVED = "observed"
    DERIVED = "derived"


class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    kind: ObservationKind
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: list[str] = Field(default_factory=list, max_length=32)


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: int = Field(ge=0)
    maximum: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_range(self) -> Health:
        if self.maximum and self.current > self.maximum:
            raise ValueError("current cannot exceed maximum")
        return self


class Power(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=64)
    current: int = Field(ge=0)
    maximum: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_range(self) -> Power:
        if self.maximum and self.current > self.maximum:
            raise ValueError("current cannot exceed maximum")
        return self


class PlayerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=128)
    realm: str | None = Field(default=None, max_length=128)
    server: str | None = Field(default=None, max_length=128)
    class_: str | None = Field(default=None, alias="class", max_length=64)
    spec: str | None = Field(default=None, max_length=128)
    level: int | None = Field(default=None, ge=0, le=1000)
    health: Health | None = None
    power: list[Power] = Field(default_factory=list, max_length=32)
    combat_state: CombatState = CombatState.UNKNOWN
    alive: bool | None = None


class TargetState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=128)
    type: str = Field(default="unknown", max_length=32)
    health: Health | None = None
    hostility: str = Field(default="unknown", max_length=32)
    level: int | None = Field(default=None, ge=0, le=1000)
    aura_summary: list[str] = Field(default_factory=list, max_length=64)


class SourceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = Field(min_length=1, max_length=128)
    profile: str = Field(min_length=1, max_length=128)


class CapabilitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CapabilityStatus
    evidence_level: EvidenceLevel

    def is_observable(self) -> bool:
        return self.status in {CapabilityStatus.AVAILABLE, CapabilityStatus.LIMITED}


class UGSState(BaseModel):
    """Validated, game-independent state accepted by Core.

    This boundary validates structure and provenance; it never authorizes actions.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: str = Field(pattern=r"^1\.\d+$", max_length=16)
    state_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=0)
    observed_at: datetime
    ingested_at: datetime
    source: SourceIdentity
    capabilities: dict[str, CapabilitySnapshot] = Field(default_factory=dict, max_length=128)
    player: PlayerState | None = None
    targets: list[TargetState] = Field(default_factory=list, max_length=64)
    events: list[AdapterEvent] = Field(default_factory=list, max_length=128)
    data_quality: DataQuality = DataQuality.UNKNOWN
    missing_signals: list[str] = Field(default_factory=list, max_length=128)
    provenance: list[str] = Field(default_factory=list, max_length=128)

    @field_validator("missing_signals", "provenance")
    @classmethod
    def bounded_metadata(cls, value: list[str]) -> list[str]:
        if any(not item or len(item) > 128 for item in value):
            raise ValueError("UGS metadata entries must be non-empty and <=128 characters")
        return value

    @field_validator("capabilities")
    @classmethod
    def capability_names_bounded(cls, value: dict[str, CapabilitySnapshot]) -> dict[str, CapabilitySnapshot]:
        if any(not key or len(key) > 128 for key in value):
            raise ValueError("UGS capability names must be non-empty and <=128 characters")
        return value

    @model_validator(mode="after")
    def validate_semantics(self) -> UGSState:
        if self.ingested_at.tzinfo is None or self.observed_at.tzinfo is None:
            raise ValueError("UGS timestamps must include timezone information")
        if self.ingested_at < self.observed_at:
            raise ValueError("ingested_at cannot precede observed_at")
        for event in self.events:
            if event.sequence > self.sequence:
                raise ValueError("event sequence cannot exceed state sequence")
            if event.schema_version.split(".")[0] != self.schema_version.split(".")[0]:
                raise ValueError("event and UGS schema major versions must match")
        return self


class UGSIngestor:
    """Small state machine enforcing duplicate/order/staleness rules per session."""

    def __init__(self, *, freshness_seconds: float = 10.0) -> None:
        if freshness_seconds <= 0:
            raise ValueError("freshness_seconds must be positive")
        self.freshness_seconds = freshness_seconds
        self._last_sequence: dict[str, int] = {}
        self._last_state: dict[str, UGSState] = {}

    def accept(self, state: UGSState) -> bool:
        previous = self._last_sequence.get(state.session_id)
        if previous is not None and state.sequence <= previous:
            return False
        self._last_sequence[state.session_id] = state.sequence
        self._last_state[state.session_id] = state
        return True

    def last_known_good(self, session_id: str) -> UGSState | None:
        return self._last_state.get(session_id)

    def is_fresh(self, state: UGSState, *, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must include timezone information")
        age = (now - state.observed_at).total_seconds()
        return 0 <= age <= self.freshness_seconds

    def usable_capability(self, state: UGSState, capability_name: str) -> bool:
        capability = state.capabilities.get(capability_name)
        return capability is not None and capability.is_observable()

    def expire(self, *, session_id: str, now: datetime) -> UGSState | None:
        state = self._last_state.get(session_id)
        if state is None or self.is_fresh(state, now=now):
            return state
        return state.model_copy(update={
            "data_quality": DataQuality.UNKNOWN,
            "missing_signals": sorted(set(state.missing_signals) | {"stale_state"}),
        })
