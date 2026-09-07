from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.core.game_adapter import CapabilityStatus, DataQuality, EvidenceLevel
from app.core.wow_adapter import ConservativeWowAdapter, WowObservation, WowPatchProfile, WowServerProfile


OBSERVED_AT = datetime(2026, 9, 7, 8, 30, tzinfo=timezone.utc)


def test_identity_is_patch_and_environment_specific():
    identity = ConservativeWowAdapter().identity(
        patch_profile=WowPatchProfile.WOTLK_3_3_5A,
        server_profile=WowServerProfile.PRIVATE,
        environment_id="wotlk-private-335a",
    )
    assert identity.game_id == "world-of-warcraft"
    assert identity.client_version == "wotlk-3.3.5a"
    assert identity.server_profile == "private"
    assert identity.environment_id == "wotlk-private-335a"


def test_capabilities_remain_unverified_without_l3_evidence():
    capabilities = ConservativeWowAdapter().capabilities(observed_at=OBSERVED_AT)
    assert len(capabilities) == 8
    assert all(cap.status == CapabilityStatus.UNVERIFIED for cap in capabilities.values())
    assert all(cap.evidence_level == EvidenceLevel.L1 for cap in capabilities.values())
    assert all("no-action-authorization" in cap.constraints for cap in capabilities.values())


def test_normalize_emits_only_passive_observation_data():
    event = ConservativeWowAdapter().normalize(WowObservation(
        event_id="obs-1",
        observed_at=OBSERVED_AT,
        sequence=4,
        patch_profile=WowPatchProfile.WOTLK_3_3_5A,
        server_profile=WowServerProfile.PRIVATE,
        realm_id="realm-1",
        latency_ms=47,
        addon_connected=True,
        launcher_associated=False,
        account_entitled=True,
        combat_state="IN_COMBAT",
        data_quality=DataQuality.MEDIUM,
        provenance=["addon"],
    ))
    assert event.event_type == "wow.passive_observation"
    assert event.sequence == 4
    assert event.payload["patch_profile"] == "wotlk-3.3.5a"
    assert event.payload["latency_ms"] == "47"
    assert event.payload["addon_connected"] == "true"
    assert "action" not in event.payload


def test_observation_rejects_out_of_bound_latency_and_unknown_fields():
    with pytest.raises(ValidationError):
        WowObservation(
            event_id="obs-1", observed_at=OBSERVED_AT, sequence=1,
            patch_profile=WowPatchProfile.RETAIL_12_0_5, latency_ms=60_001,
        )
    with pytest.raises(ValidationError):
        WowObservation(
            event_id="obs-1", observed_at=OBSERVED_AT, sequence=1,
            patch_profile=WowPatchProfile.RETAIL_12_0_5, execute_action="cast",
        )


def test_all_supported_patch_profiles_have_an_explicit_mapping():
    adapter = ConservativeWowAdapter()
    for profile in WowPatchProfile:
        identity = adapter.identity(patch_profile=profile)
        assert identity.client_version == profile.value
