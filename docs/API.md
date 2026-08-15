# SENTINEL CORE API — RC1

The running FastAPI service publishes OpenAPI at `/openapi.json` and Swagger UI at `/docs`.

## Public health

- `GET /healthz`

## User authentication

- `POST /v1/auth/register` — create an account with an email and password; returns a user session.
- `POST /v1/auth/login` — authenticate an existing account and issue a user session.
- User passwords are stored only as salted scrypt password hashes.
- User sessions have a nullable device binding and receive only non-device scopes until device proof succeeds.

## Device identity

- `POST /v1/devices/register` — authenticated user-bound enrollment, public-key fingerprint validation. The legacy enrollment-token path remains supported for non-user bootstrap flows.
- `POST /v1/devices/{device_id}/prove` — P-256 signed challenge proof and opaque device-bound session issuance.

## Sessions

- `POST /v1/sessions/refresh` — one-time refresh rotation; user sessions retain their least-privilege scope set.
- `POST /v1/sessions/revoke` — revoke the current access session.

## Authorization and events

- `POST /v1/authorize` — server-side default-deny decision.
- `POST /v1/events:batch` — device-bound, sequence-protected, idempotent event ingestion.
- `GET /v1/audit` — caller-scoped audit history.

## Game and entitlement domains

- `GET /v1/games`
- `GET /v1/games/{game_id}`
- `GET /v1/games/{game_id}/access`
- `GET /v1/admin/games`
- `GET /v1/admin/entitlements`
- `POST /v1/admin/entitlements`

## Recommendations

- `POST /v1/recommendations` — non-authoritative recommendation output with provenance.

## Authentication

Bearer access tokens are opaque values. The server stores only SHA-256 digests. Access tokens and refresh tokens are never returned in logs or audit metadata.
