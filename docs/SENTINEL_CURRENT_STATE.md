# SENTINEL — Canonical Current State

**State record:** 2026-08-31  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `2098279cd7cdb9185e8f8ca24a2c95ef27719468`  
**Prior documented product SHA:** `df05742ec609fd8e73576dc83ff10e86b2a82319`  
**Current product change on main:** PR #101 — docs: sync CURRENT_STATE to main HEAD; archive historical docs

> Git/main is authoritative for product state. Historical branch evidence is not current product state unless merged.  
> This file is the **sole source of truth** for current repository state. README, HANDOVER, PROJECT_STATE and audit snapshots must not be treated as current HEAD evidence.

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
- In-process `RateLimiter` is bounded (`RATE_LIMIT_MAX_BUCKETS`, default 10000) and evicts inactive buckets outside the active window; active buckets are never displaced for capacity. **Implementation is on branch `p1/bound-rate-limit-state-97` (issue #97); not yet merged to main.**
- Android backup is disabled; cleartext traffic is disabled; network security config is present.
- Release APK is minified/shrunk and CI verifies signing certificate fingerprint and rejects debuggable/debug artifacts.
- Authoritative release certificate fingerprint: `2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`.

## 3. Current exact-HEAD CI evidence

Current `main` HEAD: `2098279cd7cdb9185e8f8ca24a2c95ef27719468` (docs merge of PR #101).

| Workflow | Run ID | Result |
|---|---|---|
| Deploy | UNVERIFIED at this SHA | expected external pattern when no `release.published` |
| Build & Test | UNVERIFIED | exact-head run ID not independently extracted in this state sync |
| Security | UNVERIFIED | exact-head run ID not independently extracted in this state sync |
| ALPHA-0 Android CI | UNVERIFIED | exact-head run ID not independently extracted in this state sync |
| P1 Evidence | UNVERIFIED | exact-head run ID not independently extracted in this state sync |
| Release Candidate Artifact | UNVERIFIED | exact-head run ID not independently extracted in this state sync |

Historical product evidence on prior SHAs remains historical only. Treat any numeric coverage/run claims as **UNVERIFIED** for current HEAD until re-extracted against `2098279…`.

## 4. Module verification state

### `server/`

Previous exact-head verification on prior product SHAs reported core tests, coverage gate, PostgreSQL integration/recovery, migrations, security, container build and runtime smoke/health. Current state-sync evidence for `2098279…` is **UNVERIFIED** pending exact run-ID refresh.

### `app/`

Previous exact-head verification reported Android unit/JVM tests, debug/release builds, instrumentation on GitHub Emulator, signing fingerprint verification and release artifact generation. Current state-sync evidence for `2098279…` is **UNVERIFIED** pending exact run-ID refresh.

### `web/`

Previous exact-head verification reported lint and production build. Current state-sync evidence for `2098279…` is **UNVERIFIED** pending exact run-ID refresh.

### `launcher/`

Source tree exists. No dedicated test/coverage evidence established. Readiness **UNVERIFIED**.

### `wow-addon/`

Classic and Retail source trees exist. No dedicated test/coverage evidence established. Readiness **UNVERIFIED**.

## 5. External activation state

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production `DATABASE_URL` and deployment secrets.
- Real-device acceptance pass before public distribution.
- Release tag and GitHub Release publication when the operator chooses the release channel.
- Firebase Test Lab GCS `storage.objects.create` permission (issues #59 / #62 remain open).
- Branch-protection required-status-check configuration is not re-asserted in this state sync.

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
- PR #99 merged: executor assignment and standard task template.

### Issue #9 — least-privilege / secrets boundary audit — COMPLETE

- PR #85 merged.
- Removed secret length metadata echoes from Build & Test.
- Audit record: `docs/SENTINEL_SECURITY_BOUNDARY_AUDIT_ISSUE9.md`.

### PR #82 — physical-device diagnostic logging — MERGED

- Merged into `main`.
- Real physical-device acceptance remains an external operator gate.

### PR #96 — Android refresh-token lifecycle — MERGED

- Merged into `main` at `f37eb69c85aca7bb7ba143fd570ff19c495dcf03`.

### PR #99 — workflow contract executor assignment — MERGED

- Merged 2026-08-31T04:51:01Z into `main` as `df05742ec609fd8e73576dc83ff10e86b2a82319`.

### PR #101 — docs hygiene / CURRENT_STATE sync — MERGED

- Merged into `main` as `2098279cd7cdb9185e8f8ca24a2c95ef27719468`.

### Issue #97 — bound and evict process-local rate-limit state — IMPLEMENTATION ON BRANCH

- Branch: `p1/bound-rate-limit-state-97` (fresh from main `2098279…`; do **not** reuse closed PR #98 / old `p1/bound-rate-limit-state`).
- Changes: `server/app/main.py` (`RateLimiter` + `RATE_LIMIT_MAX_BUCKETS`), `server/tests/test_rate_limiter.py`, this state file.
- Semantics: configurable max buckets (default 10000); inactive buckets outside the active window are evicted before capacity enforcement; active buckets are never displaced; existing Lock and sliding-window behaviour preserved.
- Status: **not merged**; awaiting exact-head CI green and Final Integrator / Owner acceptance.

### Open PR (as of this state sync)

- PR #100 (`ci/state-sync-gate-100`): CI governance — fail PR if code changes without CURRENT_STATE.md update. Head `2288fa5a6fe610b7793e61b135e8b44b5331c8aa`. Not merged.
- PR for issue #97 will be opened from `p1/bound-rate-limit-state-97`.

## 9. Open-work state at last reconciliation

Open issues are backlog candidates, not automatic implementation instructions. Historical issues require reconciliation against the current exact HEAD before execution.

Known open external blocker: Firebase Test Lab GCS IAM issues #59 / #62.

Open product-oriented issues include (non-exhaustive): #97 (bound rate-limit state — implementation on branch), #89 (PostgreSQL refresh concurrency tests — PR #90 merged but issue remains open), #63, #60, #24, #22, and older lane issues #4–#13.

## 10. Evidence discipline

For CI, tests, coverage, release artifacts and security claims, use exact commit SHA + workflow Run ID as evidence. Do not treat historical green runs on another SHA as evidence for current `main`.

For unresolved facts, record `UNVERIFIED` rather than infer a state from source-tree presence or historical documentation.

## 11. Documentation hygiene (this pass)

- `README.md` no longer embeds canonical HEAD/SHA tables; it points here.
- `HANDOVER_DOCUMENT.md` and selected historical docs are marked ARCHIVED.
- `docs/CI_VALIDATION_NOTE.md` removed (25-byte placeholder).
