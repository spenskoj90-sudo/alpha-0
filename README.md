# SENTINEL / ALPHA-0

Security-first modular monolith with Android, SENTINEL CORE and a web control plane.

## Current implementation baseline

- Android Device Identity: Android Keystore EC/secp256r1 + SHA-256 fingerprint
- Device key lifecycle: GENERATED → ACTIVE → ROTATING → REVOKED
- Replay protection: one-time challenge + timestamp window
- Local-first event queue and game adapter contract
- Compose character dashboard
- Secure AES-GCM session storage backed by Android Keystore
- FastAPI SENTINEL CORE vertical slice
- RBAC + scope + policy authorization engine with default deny
- Device registration and ECDSA proof verification
- Backend session issuance and revocation-ready session model
- Idempotent game event ingestion with sequence replay protection
- Audit event capture
- Knowledge/recommendation contract with confidence and provenance
- PostgreSQL schema and indexes
- Next.js web dashboard design baseline
- Full architecture and Mermaid diagrams in `docs/ARCHITECTURE_V4.md`

## Repository structure

- `app/` — Android client
- `server/` — SENTINEL CORE FastAPI service
- `web/` — Next.js personal control plane
- `docs/` — architecture and intelligence contracts

## Acceptance rule

Code is not considered implemented until it has been built and tested.

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

The current branch contains the implementation baseline; CI acceptance remains the authoritative gate for release readiness.
