from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.game_adapter import AdapterEvent, AdapterIdentity, Capability, CapabilityStatus, DataQuality, EvidenceLevel, normalize_event


class WowPatchProfile(StrEnum):
    RETAIL_12_0_5 = "retail-12.0.5"
    VANILLA_1_12 = "vanilla-1.12"
    TBC_2_4_3 = "tbc-2.4.3"
    WOTLK_3_3_5A = "wotlk-3.3.5a"
    CATACLYSM_4_3_4 = "cataclysm-4.3.4"
    MOP_5_4_8 = "mop-5.4.8"
    WOD_6_2_4 = "wod-6.2.4"
    LEGION_7_3_5 = "legion-7.3.5"
    BFA_8_3_7 = "bfa-8.3.7"
    SHADOWLANDS_9_2_7 = "shadowlands-9.2.7"
    DRAGONFLIGHT_10_2_7 = "dragonflight-10.2.7"


class WowServerProfile(StrEnum):
    OFFICIAL = "official"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class WowObservation(BaseModel):
    """Passive, bounded WoW observation; it cannot encode an action."""
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=128)
    observed_at: datetime
    sequence: int = Field(ge=0)
    patch_profile: WowPatchProfile
    server_profile: WowServerProfile = WowServerProfile.UNKNOWN
    realm_id: str | None = Field(default=None, max_length=128)
    latency_ms: int | None = Field(default=None, ge=0, le=60_000)
    addon_connected: bool | None = None
    launcher_associated: bool | None = None
    account_entitled: bool | None = None
    combat_state: str | None = Field(default=None, max_length=32)
    data_quality: DataQuality = DataQuality.UNKNOWN
    provenance: list[str] = Field(default_factory=list, max_length=16)

    @field_validator("provenance")
    @classmethod
    def validate_provenance(cls, value: list[str]) -> list[str]:
        if any(not item or len(item) > 128 for item in value):
            raise ValueError("provenance entries must be non-empty and <=128 characters")
        return value


class ConservativeWowAdapter:
    """Normalize passive WoW observations into the game-independent event envelope."""
    adapter_id = "wow-conservative"
    adapter_version = "1.0"
    capability_profile_version = "1.0"
    _capability_names = (
        "wow.identity", "wow.patch_profile", "wow.realm_profile", "wow.latency",
        "wow.addon_status", "wow.launcher_association", "wow.account_entitlement",
        "wow.passive_telemetry",
    )

    def identity(self, *, patch_profile: WowPatchProfile, server_profile: WowServerProfile = WowServerProfile.UNKNOWN, environment_id: str | None = None) -> AdapterIdentity:
        return AdapterIdentity(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            game_id="world-of-warcraft",
            client_family=patch_profile.value.split("-")[0],
            client_version=patch_profile.value,
            server_profile=server_profile.value,
            environment_id=environment_id,
            capability_profile_version=self.capability_profile_version,
        )

    def capabilities(self, *, observed_at: datetime) -> dict[str, Capability]:
        return {
            name: Capability(
                status=CapabilityStatus.UNVERIFIED,
                evidence_level=EvidenceLevel.L1,
                source=[self.adapter_id],
                updated_at=observed_at,
                constraints=["passive-observation-only", "no-action-authorization"],
            ) for name in self._capability_names
        }

    def normalize(self, observation: WowObservation) -> AdapterEvent:
        payload: dict[str, object] = {
            "patch_profile": observation.patch_profile.value,
            "server_profile": observation.server_profile.value,
        }
        optional: Mapping[str, object] = {
            "realm_id": observation.realm_id,
            "latency_ms": observation.latency_ms,
            "addon_connected": observation.addon_connected,
            "launcher_associated": observation.launcher_associated,
            "account_entitled": observation.account_entitled,
            "combat_state": observation.combat_state,
        }
        for key, value in optional.items():
            if value is not None:
                payload[key] = str(value).lower() if isinstance(value, bool) else str(value)
        return normalize_event(AdapterEvent(
            event_id=observation.event_id,
            schema_version="1.0",
            occurred_at=observation.observed_at,
            sequence=observation.sequence,
            source={"adapter_id": self.adapter_id, "game_id": "world-of-warcraft"},
            event_type="wow.passive_observation",
            payload=payload,
            data_quality=observation.data_quality,
            provenance=list(observation.provenance) or [self.adapter_id],
        ), max_payload_keys=16)
