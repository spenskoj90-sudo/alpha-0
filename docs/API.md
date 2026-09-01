# SENTINEL CORE API — RC1

The running FastAPI service publishes the live API specification at `/openapi.json` and Swagger UI at `/docs`. This document is a concise manual index of the currently implemented routes; when in doubt, `/openapi.json` is the runtime source of truth.

## Public health

- `GET /healthz` — service health check.

## User authentication

- `POST /v1/auth/register` — create an account and issue a user session.
- `POST /v1/auth/login` — authenticate an existing account and issue a user session.

## Device identity

- `POST /v1/devices/register` — register a device with a public-key fingerprint; supports authenticated user-bound enrollment and the legacy enrollment-token bootstrap path.
- `POST /v1/devices/bind` — bind a new device key to the authenticated user session.
- `GET /v1/devices/{device_id}` — read the caller-owned device state.
- `POST /v1/devices/{device_id}/prove` — consume the device challenge and verify a P-256 signed proof to issue a device-bound session.
- `POST /v1/devices/{device_id}/rotate` — rotate a caller-owned active device key and issue a new device-bound session.
- `POST /v1/devices/{device_id}/revoke` — revoke a caller-owned device and its sessions.

## Sessions

- `POST /v1/sessions/refresh` — one-time refresh-token rotation.
- `POST /v1/sessions/revoke` — revoke the current access session.

## Authorization and events

- `POST /v1/authorize` — server-side default-deny authorization decision.
- `POST /v1/events:batch` — authenticated event-batch ingestion with sequence and idempotency protections.
- `GET /v1/audit` — caller-scoped audit history.

## Integrity

- `POST /v1/integrity/nonce` — issue a short-lived server nonce for integrity attestation.
- `POST /v1/integrity/attest` — consume the nonce and perform server-side Play Integrity verification; client verdicts are not trusted.

## Characters and game catalog (Phase 1 — issue #107)

- `GET /v1/characters` — list characters owned by the authenticated caller.
- `GET /v1/characters/{character_id}` — return one caller-owned character (IDOR-protected).
- `GET /v1/games` — list the current game catalog for an authenticated caller with `game:read`.
- `GET /v1/games/{game_id}` — return a single game definition.
- `GET /v1/games/{game_id}/access` — return whether the caller has an active entitlement for the game.

## Current catalog / entitlement administration

- `GET /v1/admin/games` — list the current game catalog for an authorized administrator.
- `GET /v1/admin/entitlements` — list entitlements for an authorized administrator.
- `POST /v1/admin/entitlements` — create an entitlement for a user and game.

## World of Warcraft

- `GET /v1/wow/patches` — list known WoW patches.
- `GET /v1/wow/patches/{patch_id}` — return a specific WoW patch.
- `GET /v1/wow/realms` — list known WoW realms.
- `GET /v1/wow/realms/{realm_id}` — return a specific WoW realm.
- `POST /v1/wow/realms/{realm_id}/observations` — record an administrator-authorized realm observation.
- `GET /v1/devices/me` — return the caller's currently bound device, when present.
- `GET /v1/entitlements/me` — return the caller's entitlements with game metadata.
- `GET /v1/entitlements/{entitlement_id}` — return one caller-owned entitlement with game metadata.

## Recommendations

- `POST /v1/recommendations` — non-authoritative recommendation output with provenance.

## Planned / not yet implemented

The following remain architectural targets (Phase 2+ of #107 or later):

- Event → character projection pipeline
- Character write/update via events only (no direct mutable public write in Phase 1)
- `GET /v1/devices/challenge` (if still required by client flow)

`docs/ARCHITECTURE_V4.md` remains the architectural target and is intentionally not synchronized automatically with runtime state.

## Authentication notes

Bearer access tokens are opaque values. The server stores only SHA-256 digests. Access tokens and refresh tokens are not returned in logs or audit metadata.
