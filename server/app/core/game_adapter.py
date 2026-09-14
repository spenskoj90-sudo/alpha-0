from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CapabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    UNVERIFIED = "UNVERIFIED"


class EvidenceLevel(StrEnum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class DataQuality(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class AdapterIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = Field(min_length=1, max_length=128)
    adapter_version: str = Field(min_length=1, max_length=64)
    game_id: str = Field(min_length=1, max_length=128)
    client_family: str = Field(min_length=1, max_length=64)
    client_version: str | None = Field(default=None, max_length=128)
    server_profile: str | None = Field(default=None, max_length=128)
    environment_id: str | None = Field(default=None, max_length=128)
    capability_profile_version: str = Field(min_length=1, max_length=64)


class Capability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CapabilityStatus = CapabilityStatus.UNVERIFIED
    evidence_level: EvidenceLevel = EvidenceLevel.L1
    source: list[str] = Field(default_factory=list, max_length=16)
    updated_at: datetime
    constraints: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("source", "constraints")
    @classmethod
    def validate_items(cls, value: list[str]) -> list[str]:
        if any(not item or len(item) > 128 for item in value):
            raise ValueError("capability metadata entries must be non-empty and <=128 characters")
        return value

    def is_usable(self) -> bool:
        return self.status in {CapabilityStatus.AVAILABLE, CapabilityStatus.LIMITED}


class AdapterEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(min_length=1, max_length=32)
    occurred_at: datetime
    sequence: int = Field(ge=0)
    source: dict[str, str] = Field(min_length=1, max_length=8)
    actor: dict[str, str] = Field(default_factory=dict, max_length=8)
    subject: dict[str, str] = Field(default_factory=dict, max_length=8)
    event_type: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    data_quality: DataQuality = DataQuality.UNKNOWN
    provenance: list[str] = Field(default_factory=list, max_length=32)


class CapabilityChange(BaseModel):
    capability: str = Field(min_length=1, max_length=128)
    previous: CapabilityStatus
    current: CapabilityStatus
    changed_at: datetime


_L3_ADMISSION_AUTHORITY = object()


class _L3CapabilityAdmission:
    """Internal proof that exact-environment evidence passed the L3 validator.

    Callers must not construct this directly. The exact-environment evidence
    module issues admissions only after validating a bounded evidence bundle.
    This is a process-integrity boundary, not a cryptographic trust primitive.
    """

    __slots__ = (
        "adapter_id",
        "capability_name",
        "capability",
        "environment_id",
        "evidence_id",
        "evidence_digest_sha256",
        "_authority",
    )

    def __init__(
        self,
        *,
        adapter_id: str,
        capability_name: str,
        capability: Capability,
        environment_id: str,
        evidence_id: str,
        evidence_digest_sha256: str,
        _authority: object,
    ) -> None:
        if _authority is not _L3_ADMISSION_AUTHORITY:
            raise TypeError("L3 admissions may only be issued by the exact-environment validator")
        self.adapter_id = adapter_id
        self.capability_name = capability_name
        self.capability = capability
        self.environment_id = environment_id
        self.evidence_id = evidence_id
        self.evidence_digest_sha256 = evidence_digest_sha256
        self._authority = _authority

    def is_validated(self) -> bool:
        return self._authority is _L3_ADMISSION_AUTHORITY


def _issue_l3_capability_admission(
    *,
    adapter_id: str,
    capability_name: str,
    capability: Capability,
    environment_id: str,
    evidence_id: str,
    evidence_digest_sha256: str,
) -> _L3CapabilityAdmission:
    if capability.status != CapabilityStatus.AVAILABLE or capability.evidence_level != EvidenceLevel.L3:
        raise ValueError("L3 admission requires AVAILABLE capability with L3 evidence")
    if not adapter_id or not capability_name or not environment_id or not evidence_id:
        raise ValueError("L3 admission identity fields are required")
    if len(evidence_digest_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in evidence_digest_sha256):
        raise ValueError("L3 admission requires a lowercase SHA-256 evidence digest")
    return _L3CapabilityAdmission(
        adapter_id=adapter_id,
        capability_name=capability_name,
        capability=capability,
        environment_id=environment_id,
        evidence_id=evidence_id,
        evidence_digest_sha256=evidence_digest_sha256,
        _authority=_L3_ADMISSION_AUTHORITY,
    )


class AdapterRegistry:
    """In-memory registry for validated adapter identities and capabilities.

    This registry is deliberately not an authorization store. It only records
    what an adapter can observe and enforces the contract's evidence rules at
    the Core boundary. A raw caller cannot self-label a capability AVAILABLE:
    that transition requires a validated exact-environment L3 admission.
    """

    def __init__(self) -> None:
        self._identities: dict[str, AdapterIdentity] = {}
        self._capabilities: dict[str, dict[str, Capability]] = {}
        self._changes: list[CapabilityChange] = []

    def register(self, identity: AdapterIdentity) -> None:
        self._identities[identity.adapter_id] = identity
        self._capabilities.setdefault(identity.adapter_id, {})

    def identity(self, adapter_id: str) -> AdapterIdentity | None:
        return self._identities.get(adapter_id)

    def set_capability(
        self,
        adapter_id: str,
        capability_name: str,
        capability: Capability,
    ) -> CapabilityChange | None:
        if adapter_id not in self._identities:
            raise KeyError(f"adapter is not registered: {adapter_id}")
        if not capability_name or len(capability_name) > 128:
            raise ValueError("invalid capability name")

        # AVAILABLE is an exact-environment acceptance claim. EvidenceLevel.L3
        # alone is insufficient because a caller could otherwise fabricate the
        # label. Only _admit_l3_capability may cross this boundary.
        if capability.status == CapabilityStatus.AVAILABLE:
            raise ValueError("AVAILABLE capability requires validated exact-environment L3 admission")

        return self._store_capability(adapter_id, capability_name, capability)

    def _admit_l3_capability(self, admission: _L3CapabilityAdmission) -> CapabilityChange | None:
        if not isinstance(admission, _L3CapabilityAdmission) or not admission.is_validated():
            raise ValueError("invalid L3 capability admission")
        identity = self._identities.get(admission.adapter_id)
        if identity is None:
            raise KeyError(f"adapter is not registered: {admission.adapter_id}")
        if not identity.environment_id or identity.environment_id != admission.environment_id:
            raise ValueError("L3 admission environment does not match registered adapter identity")
        if admission.capability.status != CapabilityStatus.AVAILABLE:
            raise ValueError("L3 admission capability must be AVAILABLE")
        if admission.capability.evidence_level != EvidenceLevel.L3:
            raise ValueError("L3 admission capability must carry L3 evidence")
        return self._store_capability(admission.adapter_id, admission.capability_name, admission.capability)

    def _store_capability(
        self,
        adapter_id: str,
        capability_name: str,
        capability: Capability,
    ) -> CapabilityChange | None:
        current = self._capabilities[adapter_id].get(capability_name)
        previous_status = current.status if current else CapabilityStatus.UNAVAILABLE
        self._capabilities[adapter_id][capability_name] = capability

        if previous_status == capability.status:
            return None

        change = CapabilityChange(
            capability=capability_name,
            previous=previous_status,
            current=capability.status,
            changed_at=capability.updated_at,
        )
        self._changes.append(change)
        return change

    def capability(self, adapter_id: str, capability_name: str) -> Capability | None:
        return self._capabilities.get(adapter_id, {}).get(capability_name)

    def capabilities(self, adapter_id: str) -> dict[str, Capability]:
        return dict(self._capabilities.get(adapter_id, {}))

    def changes(self) -> tuple[CapabilityChange, ...]:
        return tuple(self._changes)

    def require_usable(self, adapter_id: str, capability_name: str) -> Capability:
        capability = self.capability(adapter_id, capability_name)
        if capability is None or not capability.is_usable():
            raise LookupError(f"capability unavailable: {capability_name}")
        return capability


def normalize_event(event: AdapterEvent, *, max_payload_keys: int = 64) -> AdapterEvent:
    """Validate and bound a normalized adapter event before Core ingestion."""
    if len(event.payload) > max_payload_keys:
        raise ValueError("adapter event payload exceeds key limit")
    if any(len(str(key)) > 128 for key in event.payload):
        raise ValueError("adapter event payload key exceeds length limit")
    return event
