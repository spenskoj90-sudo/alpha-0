from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WoWPlatform(StrEnum):
    WINDOWS = "windows"


class RealmType(StrEnum):
    OFFICIAL = "official"
    PRIVATE = "private"


@dataclass(frozen=True)
class WoWPatch:
    id: str
    label: str
    family: str
    protocol_generation: str
    supported: bool = True


@dataclass(frozen=True)
class WoWRealmProfile:
    id: str
    name: str
    realm_type: RealmType
    patch_id: str
    source: str
    monitoring_profile: str
    client_integration: str
    enabled: bool = True


WOW_PATCHES: tuple[WoWPatch, ...] = (
    WoWPatch("retail-12.0.5", "Retail / Midnight 12.0.5", "retail", "retail-12"),
    WoWPatch("vanilla-1.12", "Vanilla 1.12", "classic", "classic-1"),
    WoWPatch("tbc-2.4.3", "The Burning Crusade 2.4.3", "classic", "classic-2"),
    WoWPatch("wotlk-3.3.5a", "Wrath of the Lich King 3.3.5a", "classic", "classic-3"),
    WoWPatch("cata-4.3.4", "Cataclysm 4.3.4", "classic", "classic-4"),
    WoWPatch("mop-5.4.8", "Mists of Pandaria 5.4.8", "classic", "classic-5"),
    WoWPatch("wod-6.2.4", "Warlords of Draenor 6.2.4", "classic", "classic-6"),
    WoWPatch("legion-7.3.5", "Legion 7.3.5", "classic", "classic-7"),
    WoWPatch("bfa-8.3.7", "Battle for Azeroth 8.3.7", "classic", "classic-8"),
    WoWPatch("shadowlands-9.2.7", "Shadowlands 9.2.7", "classic", "classic-9"),
    WoWPatch("dragonflight-10.2.7", "Dragonflight 10.2.7", "classic", "classic-10"),
)

# Snapshot of the currently accessible MMOTOP World of Warcraft main-rating page.
# The source is time-varying; Sentinel stores the observed snapshot and never
# treats it as permanent truth. All private-server integration is passive and
# does not bypass authentication, anti-cheat, DRM, or server rules.
MMOTOP_REALM_SEEDS: tuple[WoWRealmProfile, ...] = (
    WoWRealmProfile("mmotop-uwow", "Uwow", RealmType.PRIVATE, "legion-7.3.5", "MMOTOP", "legion-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-skyblood", "SkyBlood", RealmType.PRIVATE, "legion-7.3.5", "MMOTOP", "legion-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-wow-prime", "WoW-Prime", RealmType.PRIVATE, "legion-7.3.5", "MMOTOP", "custom-launcher", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-neverest", "Neverest", RealmType.PRIVATE, "wotlk-3.3.5a", "MMOTOP", "wotlk-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-epicwow", "EpicWoW", RealmType.PRIVATE, "legion-7.3.5", "MMOTOP", "legion-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-1001wow", "1001WOW", RealmType.PRIVATE, "wotlk-3.3.5a", "MMOTOP", "wotlk-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-northwind", "Northwind", RealmType.PRIVATE, "vanilla-1.12", "MMOTOP", "vanilla-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-poligon7", "Poligon7", RealmType.PRIVATE, "vanilla-1.12", "MMOTOP", "vanilla-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-nozdor", "Nozdor", RealmType.PRIVATE, "wotlk-3.3.5a", "MMOTOP", "wotlk-private", "launcher-plus-addon"),
    WoWRealmProfile("mmotop-turbo-wow", "Turbo-WoW", RealmType.PRIVATE, "dragonflight-10.2.7", "MMOTOP", "dragonflight-private", "launcher-plus-addon"),
)


def get_patch(patch_id: str) -> WoWPatch | None:
    return next((item for item in WOW_PATCHES if item.id == patch_id), None)


def get_realm(realm_id: str) -> WoWRealmProfile | None:
    return next((item for item in MMOTOP_REALM_SEEDS if item.id == realm_id), None)
