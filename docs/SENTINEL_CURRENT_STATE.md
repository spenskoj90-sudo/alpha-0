# SENTINEL — Canonical Current State

**State record:** 2026-09-01  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `cd87d409935c8b59f7d760beab7588c1fbf8cd67`  
**Current product change on main:** PR #110 — docs: sync CURRENT_STATE and TASKS after PR #109 (merged)

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

Current `main` HEAD is `cd87d409935c8b59f7d760beab7588c1fbf8cd67`, the merge commit for PR #110.

Product CI on this exact SHA (as of state record):

| Workflow | Run ID | Conclusion |
|----------|--------|------------|
| Security | 33517849001 | success |
| ALPHA-0 Android CI | 33517848878 | success |
| P1 Evidence | 33517848977 | success |
| Release Candidate Artifact | 33517848917 | success |
| Build & Test | 33517848953 | was in_progress at earlier record; confirm completion independently |
| Deploy | 33517846686 | failure (expected — external DEPLOY_* secrets) |

Prior HEAD `7f795596…` (PR #109): Build & Test run `33506277514` = **success**.

Numeric coverage remains **UNVERIFIED** until a completed Build & Test run ID for the current HEAD is independently confirmed.

## 3. Module verification state

### `server/`
Rate-limit bounding/eviction is merged in PR #104.

### `app/`
Sentry Android runtime observability is merged in PR #105. Android CI on HEAD `cd87d409…`: success (run 33517848878).

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

- **PR #110 — docs sync after #109: COMPLETE / MERGED.** Merge commit `cd87d409935c8b59f7d760beab7588c1fbf8cd67`.
- **Issue #12 / PR #109 — Supabase production database hosting boundary: COMPLETE / MERGED.** Merge commit `7f795596df6d7d0362fa2113aafe74daa167cd81`.
- **Issue #7 / PR #105 — Sentry Android runtime observability: COMPLETE / MERGED.** Merge commit `38184d3cb8b81c1ff2470327de104e1cc57e50a9`.
- **Issue #97 / PR #104 — bounded and evicted process-local rate-limit state: COMPLETE / MERGED.**
- **PR #100 — CI state-sync enforcement: COMPLETE / MERGED.** Merge commit `1df91de661c8bb0946d68f1671cbabf5f9714455`.
- **PR #101 — repository documentation hygiene/state synchronization: COMPLETE / MERGED.**
- **PR #103 — Android emulator runner pin: COMPLETE / MERGED.**
- **PR #108 — docs(api): align API index with runtime: COMPLETE / MERGED.** Merge commit `8af71e183f802fd156384268d128bef952100e07`.

## 7. Branch hygiene (issue #22) — Owner decision 2026-09-01

Classification performed against `main` @ `cd87d409…`. Owner decision: **delete groups 1+2; retain group 3 for manual comparison**.

### Group 1 — tip is ancestor of main (ahead = 0) — DELETE

| Branch | Tip SHA |
|--------|---------|
| `ci/state-sync-gate-100-rebased` | `f37eb69c85aca7bb7ba143fd570ff19c495dcf03` |
| `docs/supabase-hosting-sync` | `8af71e183f802fd156384268d128bef952100e07` |
| `docs/workflow-contract-14` | `997addee27e08624649deb770938108150206c4e` |
| `fix/emulator-runner-tag-102` | `df05742ec609fd8e73576dc83ff10e86b2a82319` |

### Group 2 — squash-merged content on main, tip SHA unique — DELETE

| Branch | Tip SHA | Delivered via |
|--------|---------|---------------|
| `p1/android-refresh-lifecycle-95` | `65df1a84a5ff9673a26176bb9b626de09fb24a55` | PR #96 |
| `p1/android-session-persistence-93` | `61da525554dcbcc007828356e5747c0fc9ca92c5` | PR #94 |
| `p1/issue-89-refresh-concurrency` | `272978094141b7dfc53262ab2d0a1b6802ed51ab` | PR #90 |
| `docs/hygiene-archive-state-sync-2026-08-31` | `3563f5568d4d5d27fa04d4ec70be6d1daf585104` | PR #101 |
| `docs/workflow-contract-executor-assignment` | `07a48cd5ed20ae07b568398e19c874a10b5de551` | PR #99 |
| `security/least-privilege-secrets-audit-9-clean` | `679e2d71f9f45771f9daa2a07538d843f98bc71a` | issue #9 lineage |

### Group 3 — RETAIN until Owner manual comparison

| Branch | Tip SHA |
|--------|---------|
| `feature/physical-device-diagnostics-2026-08-29` | `b9c8521bb2e5dd0de741df5f1c50d21a03c079b2` |
| `ui/sentinel-observation-point-2026-08-23` | `49dd5e8bc3c50e891ad031ca9de583b70120adc3` |
| `ui/sentinel-observation-visual-system-2026-08-23` | `d313e45356795a02b98e163ac59d0c8b0ca14482` |

**Execution note:** Branch deletion is performed by Human Owner (termux / GitHub UI). Agent does not delete refs. After Owner deletes groups 1+2, issue #22 remains open until branch-protection required checks and any remaining group-3 decisions are complete.

## 8. Open work

Current open issues: #107, #63, #59, #22, #13, #11, #10, #8.

- **#107** — Backend characters/game-state domain: OPEN / planning.
- **#59** — external Firebase Test Lab IAM blocker.
- **#22** — governance: partial (classification + Owner delete decision recorded); branch protection / group-3 cleanup still open.
- #63, #13, #11, #10, #8 — planning/backlog unless separately approved.

## 9. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED** rather than infer state from historical evidence.

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.
