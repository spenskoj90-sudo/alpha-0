# SENTINEL / ALPHA-0

Security-first modular monolith with Android, SENTINEL CORE and a web control plane.

## Current release-candidate baseline

- Android Device Identity: Android Keystore EC/secp256r1 + SHA-256 fingerprint
- Device key lifecycle: GENERATED → ACTIVE → ROTATING → REVOKED
- Replay protection: one-time challenge + timestamp window + request id
- Local-first event queue and game adapter contract
- Compose character dashboard
- Secure AES-GCM session storage backed by Android Keystore
- FastAPI SENTINEL CORE vertical slice with PostgreSQL production persistence
- Centralized default-deny authorization gateway path
- Scope syntax/composition validation
- User-bound device enrollment
- Opaque access sessions with hashed server persistence
- Refresh-token rotation and replay detection
- Idempotent game event ingestion with per-device sequence protection
- Append-oriented audit event capture
- Knowledge/recommendation contract with confidence and provenance
- PostgreSQL schema, indexes and release-hardening migration
- Deterministic migration runner with checksum verification
- Production Docker Compose reference deployment
- CI compile/test/container gates
- Release acceptance gates in `docs/RELEASE_GATES.md`
- Full architecture in `docs/ARCHITECTURE_V4.md`

## Repository structure

- `app/` — Android client
- `server/` — SENTINEL CORE FastAPI service and PostgreSQL persistence
- `web/` — Next.js personal control plane
- `docs/` — architecture, security, deployment and release contracts

## Acceptance rule

Code is not considered implemented until it has been built and tested.

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

For release decisions, the exact commit must have evidence for every required gate. Missing CI or runtime evidence is **not** interpreted as a pass.
