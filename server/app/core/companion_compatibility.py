from __future__ import annotations

from dataclasses import dataclass
import re


_VERSION_RE = re.compile(r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)$")


@dataclass(frozen=True, slots=True, order=True)
class ProtocolVersion:
    """Strict major.minor version used for compatibility negotiation."""

    major: int
    minor: int

    @classmethod
    def parse(cls, value: str) -> ProtocolVersion:
        match = _VERSION_RE.fullmatch(value)
        if match is None:
            raise ValueError("version must use major.minor form")
        return cls(int(match.group("major")), int(match.group("minor")))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


def negotiate_version(offered: str, supported: tuple[str, ...]) -> str | None:
    """Select the highest supported version with the same major version."""

    offered_version = ProtocolVersion.parse(offered)
    candidates = []
    for version in supported:
        parsed = ProtocolVersion.parse(version)
        if parsed.major == offered_version.major and parsed <= offered_version:
            candidates.append(parsed)
    if not candidates:
        return None
    return str(max(candidates))


@dataclass(frozen=True, slots=True)
class CompanionCompatibilityResult:
    accepted: bool
    protocol_version: str | None
    ugs_schema_version: str | None
    adapter_contract_version: str | None
    core_protocol_version: str | None
    capability_profile: str | None
    reason_code: str


def negotiate_companion_compatibility(
    *,
    offered_protocol: str,
    supported_protocols: tuple[str, ...],
    offered_ugs_schema: str,
    supported_ugs_schemas: tuple[str, ...],
    offered_adapter_contract: str,
    supported_adapter_contracts: tuple[str, ...],
    offered_core_protocol: str,
    supported_core_protocols: tuple[str, ...],
    offered_capability_profile: str,
    supported_capability_profiles: tuple[str, ...],
) -> CompanionCompatibilityResult:
    """Negotiate every compatibility dimension or fail closed."""

    negotiated = {
        "protocol_version": negotiate_version(offered_protocol, supported_protocols),
        "ugs_schema_version": negotiate_version(offered_ugs_schema, supported_ugs_schemas),
        "adapter_contract_version": negotiate_version(
            offered_adapter_contract, supported_adapter_contracts
        ),
        "core_protocol_version": negotiate_version(offered_core_protocol, supported_core_protocols),
    }

    if any(value is None for value in negotiated.values()):
        return CompanionCompatibilityResult(
            accepted=False,
            **negotiated,
            capability_profile=None,
            reason_code="VERSION_NEGOTIATION_FAILED",
        )

    if offered_capability_profile not in supported_capability_profiles:
        return CompanionCompatibilityResult(
            accepted=False,
            **negotiated,
            capability_profile=None,
            reason_code="CAPABILITY_PROFILE_UNSUPPORTED",
        )

    return CompanionCompatibilityResult(
        accepted=True,
        **negotiated,
        capability_profile=offered_capability_profile,
        reason_code="COMPATIBILITY_ACCEPTED",
    )
