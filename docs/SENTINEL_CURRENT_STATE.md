# SENTINEL — Canonical Current State

**State record:** 2026-08-29  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `77c42069956c5103c6065c108c6aaff4f61b1341`  
**Prior documented product SHA:** `596f10b8cc0395b31f1af6e6e343b1d52d3f7ada`  
**Current product change:** PR #82 — physical-device diagnostic logging for acceptance chain  

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
- `/v1/recommendations` is authorized through `knowledge:recommend`.
- `/v1/integrity/attest` performs server-side Play Integrity verification; client verdict lists are ignored.
- Authentication login has failure tracking and configurable lockout (`SENTINEL_AUTH_LOCKOUT_THRESHOLD`, default 8).
- Android backup is disabled; cleartext traffic is disabled; network security config is present.
- Release APK is minified/shrunk and CI verifies signing certificate fingerprint and rejects debuggable/debug artifacts.

## 3. Current exact-HEAD CI evidence

Current `main` HEAD: `77c42069956c5103c6065c108c6aaff4f61b1341`.

| Workflow | Run ID | Result |
|---|---|---|
| Build & Test | 33257152909 | success |
| Security | 33257152815 | success |
| ALPHA-0 Android CI | 33257152889 | success |
| P1 Evidence | 33257152841 | success |
| Release Candidate Artifact | 33257152850 | success |
| Deploy | 33257152376 | failure (expected external pattern: `release.published` only / 0 jobs) |

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

- P1 evidence artifact generation passed in Run `33257152841`.
- Release Candidate Artifact Run `33257152850` successfully built, verified and uploaded the signed release APK.

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

Verified on exact HEAD: Android unit/JVM tests, debug/release builds, instrumentation on GitHub Emulator, signing fingerprint verification and release artifact generation. No separate numeric Android coverage was extracted.

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

- Merged into current `main`.
- Current exact-head commit message identifies the diagnostic logging change.
- Automated Android build/instrumentation/release verification passes on current HEAD.
- Real physical-device acceptance remains an external operator gate.

## 9. Open-work state at last reconciliation

Open issues must be treated as backlog candidates, not automatic implementation instructions. Historical issues require reconciliation against the current exact HEAD before execution.

Known open external blocker: Firebase Test Lab GCS IAM issues #59 / #62.

No open PRs were present at the audit timestamp.

## 10. Evidence discipline

For CI, tests, coverage, release artifacts and security claims, use exact commit SHA + workflow Run ID as evidence. Do not treat historical green runs on another SHA as evidence for current `main`.

For unresolved facts, record `UNVERIFIED` rather than infer a state from source-tree presence or historical documentation.
