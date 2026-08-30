# SENTINEL — Canonical Current State

**State record:** 2026-08-30  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `f37eb69c85aca7bb7ba143fd570ff19c495dcf03`  
**Prior documented product SHA:** `77c42069956c5103c6065c108c6aaff4f61b1341`  
**Current merged product change:** Android refresh-token lifecycle (PR #96)  

> Git/main is authoritative for product state. Historical branch evidence is not current product state unless merged.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. A claim is not accepted as verified merely because it appears in an audit, README, PR, or historical state document.

CI and release claims below are valid only for the exact SHA identified in the corresponding evidence.

## 2. Current repository facts

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Electron launcher exists under `launcher/`.
- WoW addon sources exist under `wow-addon/` with Classic and Retail implementations.
- Device identity uses Android Keystore / EC P-256 with SHA-256 public-key fingerprinting; StrongBox preferred, TEE fallback.
- Sessions use opaque tokens with hashed persistence and one-time refresh rotation; JWT is not the primary session mechanism.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence implementation when `DATABASE_URL` is configured; production startup rejects a missing `DATABASE_URL`.
- PostgresStore sets `app.service_role=true` via connect_args; FORCE RLS is applied by migration `004_p1_rls_force.sql`.
- Postgres refresh rotation is transactional and row-locked (`FOR UPDATE`) with revoke + replacement issuance in one transaction.
- `/v1/sessions/refresh` exposes the existing transactional refresh rotation contract.
- Android `AuthApi` now calls `/v1/sessions/refresh`; refresh operations are serialized client-side and successful rotation replaces the persisted token pair.
- `/v1/recommendations` is authorized through `knowledge:recommend`.
- `/v1/integrity/attest` performs server-side Play Integrity verification; client verdict lists are ignored.
- Authentication login has failure tracking and configurable lockout (`SENTINEL_AUTH_LOCKOUT_THRESHOLD`, default 8).
- Android backup is disabled; cleartext traffic is disabled; network security config is present.
- Release APK is minified/shrunk and CI verifies signing certificate fingerprint and rejects debuggable/debug artifacts.

## 3. Current exact-HEAD CI evidence

Current `main` HEAD: `f37eb69c85aca7bb7ba143fd570ff19c495dcf03`.

| Workflow | Run / evidence | Result |
|---|---|---|
| Build & Test | exact-head run for `f37eb69c` | success |
| Security | exact-head run for `f37eb69c` | success |
| ALPHA-0 Android CI | exact-head run for `f37eb69c` | success |
| P1 Evidence | exact-head run for `f37eb69c` | success |
| Release Candidate Artifact | exact-head run for `f37eb69c` | success |
| Deploy | exact-head run for `f37eb69c` | failure (expected external pattern: `release.published` only / 0 jobs) |

### Build & Test evidence

Exact-head jobs passed:

- Web build.
- PostgreSQL integration and recovery (`migrate.py` + `pytest -m postgres`).
- Core tests and coverage: `pytest -m 'not postgres' --cov=app --cov-report=term-missing --cov-fail-under=80`.
- Android build/tests, release assembly and fingerprint verification.
- Repository verification.
- Container build.
- Reproducible container build comparison.
- Deployment smoke and health.
- Android instrumentation on GitHub Emulator.

### Security evidence

Exact-head jobs passed:

- Dependency audit.
- CodeQL Python.
- CodeQL JavaScript.
- Secret and image scan (Trivy).

### P1 / release evidence

- P1 evidence artifact generation passed on the exact `f37eb69c` HEAD.
- Release Candidate Artifact successfully built, verified and uploaded the signed release APK on the exact `f37eb69c` HEAD.

### Coverage

Exact-head core coverage: **82.09%**.

- Statements: 1,312.
- Missed: 235.
- Tests passed: 78.
- Deselects: 5.
- Gate: `--cov-fail-under=80` passed.

Lower-covered core components on this exact HEAD include:

- `app/core/store.py`: 61%.
- `app/core/user_store.py`: 77%.
- `app/core/wow_api.py`: 62%.

Coverage figures above refer to the backend/core coverage command and must not be interpreted as readiness percentages for other product modules.

## 4. Module verification state

### `server/`

Verified on exact HEAD: core tests, 82.09% coverage gate, PostgreSQL integration/recovery, migrations, security, container build and runtime smoke/health.

### `app/`

Verified on exact HEAD: Android unit/JVM tests, debug/release builds, instrumentation on GitHub Emulator, signing fingerprint verification and release artifact generation. Android refresh-token lifecycle is implemented and covered by instrumentation tests. No separate numeric Android coverage was extracted.

### `web/`

Verified on exact HEAD: lint and production build. No separate numeric web coverage was extracted.

### `launcher/`

Source tree exists. No dedicated test/coverage evidence was established in the current exact-head audit. Readiness is therefore **UNVERIFIED**.

### `wow-addon/`

Classic and Retail source trees exist. No dedicated test/coverage evidence was established in the current exact-head audit. Readiness is therefore **UNVERIFIED**.

## 5. External activation state

The repository passes the automated product/security gates above, but live external services still require operator configuration or acceptance:

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production `DATABASE_URL` and deployment secrets.
- A real-device acceptance pass before public distribution.
- A release tag and GitHub Release publication when the operator chooses the release channel.
- Firebase Test Lab GCS `storage.objects.create` permission (issues #59 / #62 remain open).
- Branch-protection required-status-check configuration is not asserted here because current protection metadata was not independently verified in this state sync.

These are deployment credentials/configuration or operator acceptance items, not missing repository implementation unless separately demonstrated by current evidence.

## 6. Explicit security invariants

Do not silently change:

- opaque-token session architecture;
- Android Keystore P-256 identity model;
- default-deny authorization semantics;
- production `DATABASE_URL` / enrollment-token requirements;
- migration checksum enforcement;
- service-role/RLS boundary;
- transactional refresh rotation;
- signing secrets or production credentials.

## 7. Authority

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.

## 8. Current workflow state

### Issue #14 — task-to-PR workflow contract — COMPLETE

- PR #83 merged: `docs/WORKFLOW_CONTRACT.md` introduced.
- PR #84 and PR #86 synchronized the state/README governance requirements.

### Issue #9 — least-privilege / secrets boundary audit — COMPLETE

- PR #85 merged.
- Removed secret length metadata echoes from Build & Test.
- Audit record: `docs/SENTINEL_SECURITY_BOUNDARY_AUDIT_ISSUE9.md`.

### PR #82 — physical-device diagnostic logging — MERGED

- Merged into `main`.
- Automated Android build/instrumentation/release verification passed on subsequent exact HEADs.
- Real physical-device acceptance remains an external operator gate.

### PR #94 — Android session persistence regression coverage — MERGED

- Proved persisted session restoration, missing-session handling and clear/revocation behavior with Android instrumentation coverage.

### PR #96 — Android refresh-token lifecycle — MERGED

- Added Android refresh endpoint integration.
- Serialized concurrent refresh operations.
- Persisted rotated token pairs and handled invalid/revoked refresh as re-authentication.
- Exact merged HEAD `f37eb69c` passed the required automated product/security gates.

### Issue #97 — bound and evict process-local rate-limit state — IN PROGRESS

- Approved P1 implementation.
- Branch: `p1/bound-rate-limit-state`.
- Current work adds a configurable bucket bound and inactive-bucket eviction while preserving active-window semantics.
- Regression tests are included under `server/tests/test_rate_limiter.py`.
- This branch is **not merged** and has **no exact-PR CI acceptance yet**; do not treat it as current `main` product state.

## 9. Open-work state at last reconciliation

Open issues must be treated as backlog candidates, not automatic implementation instructions. Historical issues require reconciliation against the current exact HEAD before execution.

Known open external blocker: Firebase Test Lab GCS IAM issues #59 / #62.

No open PR was present on `main` before the current P1 branch was started; the current rate-limit work is pending PR/CI verification.

## 10. Evidence discipline

For CI, tests, coverage, release artifacts and security claims, use exact commit SHA + workflow Run ID as evidence. Do not treat historical green runs on another SHA as evidence for current `main`.

For unresolved facts, record `UNVERIFIED` rather than infer a state from source-tree presence or historical documentation.
