# SENTINEL — Canonical Current State

**State record:** 2026-08-31  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `MERGE_PENDING`  
**Prior documented product SHA:** `77c42069956c5103c6065c108c6aaff4f61b1341`  
**Current merged product change:** PR #96 — Android refresh-token lifecycle  
**Current governance work:** Issue #102 — Android emulator runner reference fix (PR #103 pending)  

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
- `/v1/sessions/refresh` exposes the transactional refresh rotation contract.
- Android `AuthApi` calls `/v1/sessions/refresh`; refresh operations are serialized client-side and successful rotation replaces the persisted token pair.
- `/v1/recommendations` is authorized through `knowledge:recommend`.
- `/v1/integrity/attest` performs server-side Play Integrity verification; client verdict lists are ignored.
- Authentication login has failure tracking and configurable lockout (`SENTINEL_AUTH_LOCKOUT_THRESHOLD`, default 8).
- Android backup is disabled; cleartext traffic is disabled; network security config is present.
- Release APK is minified/shrunk and CI verifies signing certificate fingerprint and rejects debuggable/debug artifacts.

## 3. Current exact-HEAD CI evidence

Current `main` HEAD: `MERGE_PENDING`.

| Workflow | Run ID | Result |
|---|---|---|
| Build & Test | UNVERIFIED | Pending CI on Issue #102 branch HEAD |
| Security | UNVERIFIED | Pending CI on Issue #102 branch HEAD |
| ALPHA-0 Android CI | UNVERIFIED | Pending CI on Issue #102 branch HEAD |
| P1 Evidence | UNVERIFIED | Pending CI on Issue #102 branch HEAD |
| Deploy | 33320881527 | failure (expected external pattern: `release.published` only / 0 jobs) |

### Build & Test evidence

Exact-head verification is pending for the Issue #102 branch HEAD.

### Security evidence

Exact-head verification is pending for the Issue #102 branch HEAD.

### P1 / release evidence

Exact-head verification is pending for the Issue #102 branch HEAD.

### Coverage

No new coverage claim is made for Issue #102.

## 4. Module verification state

### `server/`

Previously verified on exact HEAD `f37eb69c`; revalidation is pending for the Issue #102 branch HEAD.

### `app/`

Previously verified on exact HEAD `f37eb69c`; revalidation is pending for the Issue #102 branch HEAD.

### `web/`

Previously verified on exact HEAD `f37eb69c`; revalidation is pending for the Issue #102 branch HEAD.

### `launcher/`

Source tree exists. No dedicated test/coverage evidence was established. Readiness remains **UNVERIFIED**.

### `wow-addon/`

Classic and Retail source trees exist. No dedicated test/coverage evidence was established. Readiness remains **UNVERIFIED**.

## 5. External activation state

The repository passes the automated product/security gates above, but live external services still require operator configuration or acceptance:

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production `DATABASE_URL` and deployment secrets.
- A real-device acceptance pass before public distribution.
- A release tag and GitHub Release publication when the operator chooses the release channel.
- Firebase Test Lab GCS `storage.objects.create` permission (issues #59 / #62 remain open).
- Branch-protection required-status-check configuration is now asserted on `main` for `Secret and image scan` and `Core tests and coverage`.

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
- PR #86 added strict README/CURRENT_STATE synchronization requirements.

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

### Issue #100 — CI state-sync enforcement — IN REVIEW

- Separate governance PR; not the implementation vehicle for Issue #102.

### Issue #101 — repository hygiene — MERGED

- PR #101 merged into `main`.
- Historical documentation was archived/marked appropriately and README canonical-state references were synchronized.

### Issue #102 — Android emulator runner reference fix — IN REVIEW

- PR #103.
- Changes `.github/workflows/build.yml` to use `ReactiveCircus/android-emulator-runner@v2.37.0`.
- Existing emulator parameters and script are preserved.
- This branch is rebased/reconciled with the post-#101 `main` state; hygiene changes from #101 are preserved.

### PR #99 — workflow contract executor assignment and standard task template — OPEN

- Separate governance documentation PR.
- Not the implementation vehicle for Issue #102.

## 9. Open-work state at last reconciliation

Open issues must be treated as backlog candidates, not automatic implementation instructions. Historical issues require reconciliation against the current exact HEAD before execution.

Known open external blocker: Firebase Test Lab GCS IAM issues #59 / #62.

PR #99 is unrelated to Issue #102 and remains separate.

Issue #102 is pending review under PR #103.

## 10. Evidence discipline

For CI, tests, coverage, release artifacts and security claims, use exact commit SHA + workflow Run ID as evidence. Do not treat historical green runs on another SHA as evidence for current `main`.

For unresolved facts, record `UNVERIFIED` rather than infer a state from source-tree presence or historical documentation.
