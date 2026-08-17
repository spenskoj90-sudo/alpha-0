# SENTINEL / ALPHA-0

Security-first modular monolith with Android, SENTINEL CORE and a web control plane.

## Canonical repository state

- Canonical branch: `main`
- Canonical HEAD at the 2026-08-17 state reconciliation: `70702f3f992097cea9553c406b5d8febb3a47539`
- Branch/PR work is **not** part of the product state until merged into `main` and revalidated at the resulting main SHA.
- Architecture documents describe the target/contract and must not be treated as proof of runtime implementation.
- The authoritative state record is [`docs/SENTINEL_CURRENT_STATE.md`](docs/SENTINEL_CURRENT_STATE.md).
- The evidence/acceptance rules are [`docs/SENTINEL_EVIDENCE_PROTOCOL.md`](docs/SENTINEL_EVIDENCE_PROTOCOL.md).
- Engineering decisions are recorded in [`docs/SENTINEL_DECISION_LOG.md`](docs/SENTINEL_DECISION_LOG.md).

## Current implementation baseline on `main`

- Android Device Identity foundation using Android Keystore EC/secp256r1 and SHA-256 fingerprinting
- Device key lifecycle foundation
- One-time challenge/expiration/consumption security primitives
- Compose character dashboard
- Secure Android session-storage foundation
- FastAPI SENTINEL CORE vertical slice
- RBAC + scope + policy authorization engine with explicit default deny
- Device registration and ECDSA proof verification
- Backend session model
- Game event ingestion foundations and replay/idempotency structures
- Audit event capture
- Knowledge/recommendation contract with confidence/provenance
- PostgreSQL schema and indexes
- Next.js/web control-plane source
- Full architecture contract in `docs/ARCHITECTURE_V4.md`

### Important current-state limitation

The PostgreSQL schema exists on `main`, but the current runtime path still uses an in-memory `MemoryStore`. Do not describe PostgreSQL as the authoritative runtime persistence layer until the runtime repository integration is merged and validated on `main`.

The Android entry point on current `main` is still a technical `CharacterDashboard` surface. Later Login/Register and multi-section product work must be treated as branch-only until verified on `main`.

## Repository structure

- `app/` — Android client
- `server/` — SENTINEL CORE FastAPI service
- `web/` — web control plane
- `docs/` — architecture, contracts, current-state and evidence records
- `.github/workflows/` — CI automation

## Acceptance rule

Code is not considered implemented until it has been built and tested on the canonical line.

`FAIL → root cause → FIX → regression → MAIN PASS → ACCEPTED`

A branch PASS or PR PASS is not equivalent to MAIN PASS.

## Repository hygiene

Use short-lived feature branches and PRs. Keep one canonical `main`. Classify historical branches before deleting them. Never overwrite historical evidence to make the repository appear cleaner; preserve the evidence and record the resulting decision in the decision log.
