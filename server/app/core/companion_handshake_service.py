from __future__ import annotations

from dataclasses import dataclass

from .companion_protocol import CompanionHandshake, CompanionHandshakeResult, negotiate_handshake


@dataclass(frozen=True, slots=True)
class CompanionCompatibility:
    ugs_schema_version: str
    adapter_contract_version: str
    core_protocol_version: str
    capability_profile: str


class CompanionHandshakeService:
    """Bounded compatibility gate around the canonical v1 handshake rules."""

    def __init__(self, compatibility: CompanionCompatibility) -> None:
        self._compatibility = compatibility

    def negotiate(self, offered: CompanionHandshake) -> CompanionHandshakeResult:
        return negotiate_handshake(
            offered,
            expected_ugs_schema=self._compatibility.ugs_schema_version,
            expected_adapter_contract=self._compatibility.adapter_contract_version,
            expected_core_protocol=self._compatibility.core_protocol_version,
            expected_capability_profile=self._compatibility.capability_profile,
        )
