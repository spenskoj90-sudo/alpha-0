# SENTINEL CORE API — Release Candidate

The running FastAPI service publishes the live API specification at `/openapi.json` and Swagger UI at `/docs`. This document is a concise manual index of the currently implemented routes; when in doubt, `/openapi.json` is the runtime source of truth.

## Public health

- `GET /healthz` — service health check.

## User authentication

- `POST /v1/auth/register` — create an account and issue a least-privilege user session.
- `POST /v1/auth/login` — authenticate an existing account and issue a least-privilege user session.

## Device identity

- `POST /v1/devices/register` — register a device with a public-key fingerprint; supports authenticated user-bound enrollment and the legacy enrollment-token bootstrap path.
- `POST /v1/devices/bind` — bind a new device key to the authenticated user session and return the first one-time proof challenge.
- `GET /v1/devices/{device_id}` — read the caller-owned device state.
- `POST /v1/devices/{device_id}/challenge` — issue a fresh one-time proof challenge for a caller-owned active device; used for proof retry without creating another device binding.
- `POST /v1/devices/{device_id}/prove` — consume the device challenge and verify a P-256 signed proof to issue a device-bound session.
- `POST /v1/devices/{device_id}/rotate` — rotate a caller-owned active device key and issue a new device-bound session.
- `POST /v1/devices/{device_id}/revoke` — revoke a caller-owned device and its sessions.

## Sessions

- `POST /v1/sessions/refresh` — one-time refresh-token rotation.
- `POST /v1/sessions/revoke` — revoke the current access session.

## Authorization and events

- `POST /v1/authorize` — server-side default-deny authorization decision.
- `POST /v1/events:batch` — authenticated event-batch ingestion with sequence and idempotency protections. Event writes require a device-bound session carrying `game:write`; ordinary login/register sessions intentionally do not carry that scope.
- `GET /v1/audit` — caller-scoped audit history.

Accepted character events are projected into the character store on a best-effort basis after durable event acceptance. Public clients do not receive a direct mutable character-write endpoint.

## Integrity

- `POST /v1/integrity/nonce` — issue a short-lived server nonce for integrity attestation.
- `POST /v1/integrity/attest` — consume the nonce and perform server-side Play Integrity verification; client verdicts are not trusted.

## Characters and game catalog

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
- `POST /v1/wow/realms/{realm_id}/observations` — accept an administrator-authorized realm observation.
- `GET /v1/devices/me` — return the caller's currently bound device, when present.
- `GET /v1/entitlements/me` — return the caller's entitlements with game metadata.
- `GET /v1/entitlements/{entitlement_id}` — return one caller-owned entitlement with game metadata.

## Recommendations

- `POST /v1/recommendations` — non-authoritative recommendation output with confidence, provenance and provider/model identity where applicable. Explicit unknown provider selection fails closed.

`docs/ARCHITECTURE_V4.md` and `docs/SENTINEL_MASTER_ARCHITECTURE_v0.3.md` define architecture targets and must not be treated as runtime route inventories.

## Authentication notes

Bearer access tokens are opaque values. The server stores only SHA-256 digests. Access tokens, refresh tokens, proof signatures and raw private-key material are not returned in logs or audit metadata.
