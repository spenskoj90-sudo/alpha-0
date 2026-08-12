# SENTINEL / ALPHA-0

Security-first modular monolith with Android, SENTINEL CORE and a web control plane.

## Release candidate baseline

**Version: 1.0.0-RC1**

- Android Device Identity: Android Keystore EC/secp256r1 + SHA-256 fingerprint
- Device key lifecycle: GENERATED → ACTIVE → ROTATING → REVOKED
- Replay protection: one-time challenge + timestamp window
- Local-first event queue and game adapter contract
- Compose character dashboard
- FastAPI SENTINEL CORE vertical slice
- RBAC + scope + policy authorization engine with default deny
- Device registration and ECDSA proof verification
- Backend session issuance with hashed opaque session identifiers
- Idempotent game event ingestion with sequence replay protection
- Audit event capture
- Knowledge/recommendation contract with confidence and provenance
- PostgreSQL schema and indexes
- Production container/deployment contract
- OpenAPI 3.0.3 contract
- Full architecture and Mermaid diagrams in `docs/ARCHITECTURE_V4.md`
- Implementation Contract v1 in `docs/IMPLEMENTATION_CONTRACT_V1.md`
- Test Matrix v1 in `docs/TEST_MATRIX_V1.md`

## Repository structure

- `app/` — Android client
- `server/` — SENTINEL CORE FastAPI service
- `web/` — Next.js personal control plane
- `docs/` — architecture, implementation and release contracts

## Acceptance rule

Code is not considered implemented until it has been built and tested.

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

CI acceptance is authoritative for automated release readiness. Release signing remains isolated from ordinary CI and uses the verified release keystore outside source control.
