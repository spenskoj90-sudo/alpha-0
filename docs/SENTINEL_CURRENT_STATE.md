# SENTINEL — Canonical Current State

**State record:** 2026-08-29  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `596f10b8cc0395b31f1af6e6e343b1d52d3f7ada`  
**Prior product SHA (full CI green):** `00de9f972e67895557d2198965637728ac0a75a4` (PR #85)  
**Final correction branch:** `sentinel/final-zero-gap-2026-08-28`  
**Merged PR (security completion baseline):** #70  
**Merged head:** `19a1ded90b0b68a60f07dd7efaf725a164b360b0`  

> Git/main is authoritative for product state. Historical branch evidence is not current product state unless merged.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. A claim is not accepted as verified merely because it appears in an audit, README, PR, or historical state document.

## 2. Current repository facts

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
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

## 3. Final security completion — PR #70

Merge SHA: `39bfef81aeb05581a664837260864bc2fd41cd66`

Implemented:

1. Server-side Play Integrity verifier with package/certificate/nonce/freshness checks and `PLAY_RECOGNIZED` requirement.
2. Fail-closed Play Integrity behavior when production verification configuration is absent.
3. `/v1/integrity/attest` wired to the verifier; client-supplied verdicts cannot establish trust.
4. Atomic Postgres refresh rotation and adversarial concurrency coverage.
5. Login lockout and security-failure tracking.
6. Android release minification/shrinking and Play Integrity client attestation path.
7. Release workflow uses `assembleRelease`, validates the signing certificate, rejects debug APKs, and publishes only the release APK.
8. Play Integrity regression test corrected for the full verifier configuration contract.

## 4. CI evidence for the merged product tree

### Last completed full product CI (SHA `00de9f972e67895557d2198965637728ac0a75a4`, PR #85)

| Workflow | Run ID | Result |
|---|---|---|
| Build & Test #352 | 33253833147 | success |
| Security #270 | 33253833094 | success |
| ALPHA-0 Android CI #1273 | 33253833092 | success |
| P1 Evidence #179 | 33253833099 | success |
| Release Candidate Artifact #4 | 33253833088 | success |
| Deploy | 33253832643 | failure (expected: `release.published` only; 0 jobs) |

Core unit coverage on that run: **82.09%** (78 passed, gate ≥80%).

### Current main HEAD `596f10b8…` (PR #86 docs-only merge)

| Workflow | Run ID | Result |
|---|---|---|
| Security #272 | 33256189402 | success |
| Build & Test #354 | 33256189396 | in_progress at state-record time |
| ALPHA-0 Android CI #1277 | 33256189409 | in_progress at state-record time |
| P1 Evidence #181 | 33256189431 | in_progress at state-record time |
| Deploy | 33256189041 | failure (expected external pattern) |

## 5. External activation state

The repository is production-activation ready, but live external services still require their real operator configuration:

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production `DATABASE_URL` and deployment secrets.
- A real-device acceptance pass before public distribution (PR #82 open: physical-device diagnostics).
- A release tag and GitHub Release publication when the operator chooses the release channel.
- Firebase Test Lab GCS object-create permission (issues #59 / #62).

These are deployment credentials/configuration, not missing repository implementation.

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

## 8. Closed workflow / security process issues

### Issue #14 — task-to-PR workflow contract — COMPLETE

- PR #83 merged: `docs/WORKFLOW_CONTRACT.md` introduced (`ba3c310cf79701ad812c36b3bfc32354b51b23d6`).
- PR #84: CURRENT_STATE note for #14.
- PR #86: blocking rule requiring README + CURRENT_STATE sync before merge (`596f10b8cc0395b31f1af6e6e343b1d52d3f7ada`).

### Issue #9 — least-privilege / secrets boundary audit — COMPLETE

- PR #85 merged at `00de9f972e67895557d2198965637728ac0a75a4`.
- Removed secret length metadata echoes from Build & Test.
- Audit record: `docs/SENTINEL_SECURITY_BOUNDARY_AUDIT_ISSUE9.md`.
