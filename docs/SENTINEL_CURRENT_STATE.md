# SENTINEL — Canonical Current State

**State record:** 2026-09-01  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `23ee6d2dbe0765159ce2dad9687dbd555c984cb5`  
**Current product change on main:** PR #111 — docs: record #22 branch cleanup decision (merged)

> Git/main is authoritative for product state. Historical branch evidence is not current product state unless merged.
> Exact CI/release claims require the exact SHA plus workflow Run ID; unresolved evidence is recorded as **UNVERIFIED**.

## 1. Current repository facts

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Electron launcher exists under `launcher/`.
- WoW addon sources exist under `wow-addon/` with Classic and Retail implementations.
- Device identity uses Android Keystore / EC P-256 with SHA-256 public-key fingerprinting.
- Sessions use opaque tokens with hashed persistence and one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence implementation when `DATABASE_URL` is configured; FORCE RLS is applied by migration `004_p1_rls_force.sql`.
- Production database hosting is Supabase (managed PostgreSQL, free tier) used exclusively via standard `DATABASE_URL`. Supabase Auth, managed RLS-as-service and other managed Supabase features are not used; authorization remains SENTINEL-native (see `docs/DEPLOYMENT.md` § Production database hosting).
- In-process `RateLimiter` is bounded by `RATE_LIMIT_MAX_BUCKETS` (default 10000), evicts inactive buckets before capacity enforcement, and never displaces active buckets; implemented by PR #104.
- Android backup and cleartext traffic are disabled; release signing/fingerprint gates are enforced in CI.
- Sentry Android SDK 8.54.0 is integrated for release runtime observability by PR #105. `SENTRY_DSN` is supplied only to release assembly jobs; debug/PR builds use an empty default. Privacy scrubbing is implemented in `SentinelApplication`, and Sentry auto-init is disabled so initialization is controlled by application code.

## 2. Exact-HEAD evidence

Current `main` HEAD is `23ee6d2dbe0765159ce2dad9687dbd555c984cb5`, the merge commit for PR #111.

Product CI on this exact SHA (as of state record):

| Workflow | Run ID | Conclusion |
|----------|--------|------------|
| Security | 33522199485 | success |
| ALPHA-0 Android CI | 33522199687 | success |
| P1 Evidence | 33522199461 | success |
| Release Candidate Artifact | 33522199804 | success |
| Build & Test | 33522199541 | confirm completion independently if still pending |
| Deploy | 33522197309 | failure (expected — external DEPLOY_* secrets) |

Prior HEAD `cd87d409…` (PR #110): Build & Test run `33517848953` = **success**.

Numeric coverage remains **UNVERIFIED** until a completed Build & Test run ID for the current HEAD is independently confirmed.

## 3. Module verification state

### `server/`
Rate-limit bounding/eviction is merged in PR #104.

### `app/`
Sentry Android runtime observability is merged in PR #105. Android CI on HEAD `23ee6d2d…`: success (run 33522199687).

### `web/`
Follows Build & Test result for current HEAD.

### `launcher/`
Dedicated test/coverage evidence: **UNVERIFIED**.

### `wow-addon/`
Dedicated test/coverage evidence: **UNVERIFIED**.

## 4. External activation state

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production database: Supabase (secret configured).
- Real-device acceptance before public distribution.
- Release tag and GitHub Release publication when chosen by Owner.
- Firebase Test Lab GCS `storage.objects.create` permission (issues #59).
- GitHub repository secret `SENTRY_DSN` before release builds emit Sentry events.
- Branch-protection required-status configuration remains an operator/governance concern unless independently verified.

## 5. Explicit security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.

## 6. Completed workflow state

- **PR #111 — docs: record #22 branch cleanup decision: COMPLETE / MERGED.** Merge commit `23ee6d2dbe0765159ce2dad9687dbd555c984cb5`.
- **PR #110 — docs sync after #109: COMPLETE / MERGED.** Merge commit `cd87d409935c8b59f7d760beab7588c1fbf8cd67`.
- **Issue #12 / PR #109 — Supabase production database hosting boundary: COMPLETE / MERGED.** Merge commit `7f795596df6d7d0362fa2113aafe74daa167cd81`.
- **Issue #7 / PR #105 — Sentry Android runtime observability: COMPLETE / MERGED.** Merge commit `38184d3cb8b81c1ff2470327de104e1cc57e50a9`.
- **Issue #97 / PR #104 — bounded and evicted process-local rate-limit state: COMPLETE / MERGED.**
- **PR #100 — CI state-sync enforcement: COMPLETE / MERGED.** Merge commit `1df91de661c8bb0946d68f1671cbabf5f9714455`.
- **PR #101 — repository documentation hygiene/state synchronization: COMPLETE / MERGED.**
- **PR #103 — Android emulator runner pin: COMPLETE / MERGED.**
- **PR #108 — docs(api): align API index with runtime: COMPLETE / MERGED.** Merge commit `8af71e183f802fd156384268d128bef952100e07`.

## 7. Branch hygiene (issue #22) — COMPLETE 2026-09-01

**Live branch inventory (verified after Owner deletes):** only `main` exists. No historical feature/docs/ci/p1/ui/security branches remain.

Classification and Owner execution:

| Group | Action | Count |
|-------|--------|-------|
| 1 — tip ancestor of main | Deleted by Owner | 4 |
| 2 — squash-merged content on main | Deleted by Owner | 6 |
| 3 — manual comparison (PR #82 / UI tokens on main) | Deleted by Owner after comparison | 3 |

Group 3 evidence: `feature/physical-device-diagnostics-2026-08-29` content on main via PR #82 (`DiagnosticLogger` + instrumentation); UI observation branches superseded by `DesignTokens.kt` / `SentinelTheme.kt` on main.

**Remaining for #22:** configure required status checks / branch protection on `main` (operator-only). Historical branch cleanup is done.

## 8. Open work

Current open issues: #107, #63, #59, #22, #13, #11, #10, #8.

- **#107** — Backend characters/game-state domain: OPEN / planning.
- **#59** — external Firebase Test Lab IAM blocker.
- **#22** — governance: historical branch cleanup **COMPLETE**; branch-protection required checks still open (operator).
- #63, #13, #11, #10, #8 — planning/backlog unless separately approved.

## 9. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED** rather than infer state from historical evidence.

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.
