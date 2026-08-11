# SENTINEL World of Warcraft Support

## Supported patch profiles

- Retail / Midnight 12.0.5 (current verified official content-update baseline at the time of this change)
- Vanilla 1.12
- The Burning Crusade 2.4.3
- Wrath of the Lich King 3.3.5a
- Cataclysm 4.3.4
- Mists of Pandaria 5.4.8
- Warlords of Draenor 6.2.4
- Legion 7.3.5
- Battle for Azeroth 8.3.7
- Shadowlands 9.2.7
- Dragonflight 10.2.7

Blizzard's current content notes show Midnight 12.0.5 as the active Retail content update. The patch catalog is deliberately data-driven so future Retail patches can be inserted without changing the authorization model.

## MMOTOP snapshot

The currently accessible MMOTOP World of Warcraft main-rating page exposed this top-10 snapshot:

1. Uwow — Legion Plus, 7.3.5
2. SkyBlood — 7.3.5
3. WoW-Prime — custom/launcher profile
4. Neverest — WotLK-era profile, 3.3.5a
5. EpicWoW — Legion 7.3.5
6. 1001WOW — 3.3.5a
7. Northwind — Vanilla 1.12.1
8. Poligon7 — Classic 1.12 profile
9. Nozdor — WotLK-era profile, 3.3.5a
10. Turbo-WoW — Dragonflight 10.2.7

MMOTOP is time-varying. Sentinel stores this as a snapshot and must refresh it before presenting a claim that it is the current live top-10. The source page also lists additional servers such as WoW Circle, Diablo-WOW and Moonwell below this snapshot.

## Integration boundary

Sentinel supports identification, version/realm classification, passive telemetry, latency/status observations, local addon status, launcher association and account entitlement checks. It does not bypass authentication, DRM, anti-cheat, server access controls, rate limits, or game integrity mechanisms.

## Overlay

The addon uses a movable 330x150 panel anchored by default at TOPRIGHT (-24,-90). It contains:

- protection state;
- realm and server type field;
- ping;
- patch profile;
- passive telemetry mode;
- green/yellow/red session indicator;
- PAUSE, SETTINGS, SCREENSHOT and LOCK controls.

LOCK is a Sentinel session/UI lock only. It does not claim to lock a Blizzard or private-server account.

## API

- GET /v1/wow/patches
- GET /v1/wow/patches/{patch_id}
- GET /v1/wow/realms
- GET /v1/wow/realms/{realm_id}
- POST /v1/wow/realms/{realm_id}/observations (admin token required)
