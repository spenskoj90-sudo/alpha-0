import pytest

from app.core.companion_compatibility import (
    CompanionCompatibilityResult,
    ProtocolVersion,
    negotiate_companion_compatibility,
    negotiate_version,
)


def test_protocol_version_is_strict_and_orderable() -> None:
    assert ProtocolVersion.parse("1.2") < ProtocolVersion.parse("1.3")
    assert str(ProtocolVersion.parse("2.0")) == "2.0"
    with pytest.raises(ValueError):
        ProtocolVersion.parse("1")
    with pytest.raises(ValueError):
        ProtocolVersion.parse("1.x")


def test_negotiation_selects_highest_supported_not_newer_than_offer() -> None:
    assert negotiate_version("1.4", ("1.0", "1.2", "1.3")) == "1.3"
    assert negotiate_version("1.2", ("1.0", "1.2", "1.3")) == "1.2"


def test_negotiation_rejects_major_version_downgrade() -> None:
    assert negotiate_version("2.0", ("1.0", "1.3")) is None
    assert negotiate_version("1.0", ("2.0",)) is None


def test_companion_compatibility_negotiates_all_dimensions() -> None:
    result = negotiate_companion_compatibility(
        offered_protocol="1.3",
        supported_protocols=("1.0", "1.2"),
        offered_ugs_schema="1.2",
        supported_ugs_schemas=("1.0", "1.1"),
        offered_adapter_contract="1.1",
        supported_adapter_contracts=("1.0", "1.1"),
        offered_core_protocol="1.4",
        supported_core_protocols=("1.1", "1.3"),
        offered_capability_profile="wow.passive.v1",
        supported_capability_profiles=("wow.passive.v1",),
    )

    assert result == CompanionCompatibilityResult(
        accepted=True,
        protocol_version="1.2",
        ugs_schema_version="1.1",
        adapter_contract_version="1.1",
        core_protocol_version="1.3",
        capability_profile="wow.passive.v1",
        reason_code="COMPATIBILITY_ACCEPTED",
    )


def test_companion_compatibility_fails_closed_if_any_version_has_no_match() -> None:
    result = negotiate_companion_compatibility(
        offered_protocol="1.3",
        supported_protocols=("1.0",),
        offered_ugs_schema="2.0",
        supported_ugs_schemas=("1.0",),
        offered_adapter_contract="1.1",
        supported_adapter_contracts=("1.0",),
        offered_core_protocol="1.1",
        supported_core_protocols=("1.0",),
        offered_capability_profile="wow.passive.v1",
        supported_capability_profiles=("wow.passive.v1",),
    )

    assert result.accepted is False
    assert result.reason_code == "VERSION_NEGOTIATION_FAILED"
    assert result.ugs_schema_version is None
    assert result.capability_profile is None


def test_capability_profile_is_exact_and_not_version_negotiated() -> None:
    result = negotiate_companion_compatibility(
        offered_protocol="1.0",
        supported_protocols=("1.0",),
        offered_ugs_schema="1.0",
        supported_ugs_schemas=("1.0",),
        offered_adapter_contract="1.0",
        supported_adapter_contracts=("1.0",),
        offered_core_protocol="1.0",
        supported_core_protocols=("1.0",),
        offered_capability_profile="wow.passive.v2",
        supported_capability_profiles=("wow.passive.v1",),
    )

    assert result.accepted is False
    assert result.reason_code == "CAPABILITY_PROFILE_UNSUPPORTED"
    assert result.capability_profile is None
