# SENTINEL — Canonical Current State

**State record:** 2026-08-31  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `1df91de661c8bb0946d68f1671cbabf5f9714455`  
**Current branch:** `feature/sentry-android-observability-7`  
**Current branch HEAD:** `fabaead06d740ceefb771bf17858f7f3b6578769`  
**Prior documented product SHA:** `ab64505bb35d32006aa2c98940e807f3f9d87508`  
**Current product change on main:** PR #100 state-sync gate + emulator pin (merged as `1df91de…`)

> Git/main is authoritative for product state. Historical branch evidence is not current product state unless merged.  
> This file is the sole source of truth for current repository state.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. CI and release claims are valid only for the exact SHA identified in the corresponding evidence.

## 2. Current repository facts

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Electron launcher exists under `launcher/`.
- WoW addon sources exist under `wow-addon/` with Classic and Retail implementations.
- Device identity uses Android Keystore / EC P-256 with SHA-256 public-key fingerprinting.
- Sessions use opaque tokens with hashed persistence and one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence implementation when `DATABASE_URL` is configured; FORCE RLS is applied by migration `004_p1_rls_force.sql`.
- Refresh rotation is transactional and row-locked.
- `/v1/recommendations` requires `knowledge:recommend`.
- `/v1/integrity/attest` performs server-side Play Integrity verification.
- Authentication has configurable failure tracking and lockout.
- In-process `RateLimiter` is bounded by `RATE_LIMIT_MAX_BUCKETS` (default 10000), evicts inactive buckets before capacity enforcement, and never displaces active buckets. This implementation is merged in PR #104.
- Android backup and cleartext traffic are disabled; release signing/fingerprint gates are enforced in CI.
- **Sentry Android SDK (issue #7)** is integrated on branch `feature/sentry-android-observability-7`: DSN via BuildConfig from CI secret only, privacy scrubbing enabled, documented in `docs/OBSERVABILITY.md`. The Kotlin BuildConfig expressions have been corrected to use ordinary Kotlin quotes inside `${...}`; this branch change is not merged to main.

## 3. Current exact-HEAD CI evidence

Current `main` HEAD: `1df91de661c8bb0946d68f1671cbabf5f9714455`.

| Workflow | Result |
|---|---|
| Build & Test | UNVERIFIED for exact current HEAD |
| Security | UNVERIFIED for exact current HEAD |
| ALPHA-0 Android CI | UNVERIFIED for exact current HEAD |
| P1 Evidence | UNVERIFIED for exact current HEAD |
| Release Candidate Artifact | UNVERIFIED for exact current HEAD |
| Deploy | UNVERIFIED / expected external trigger pattern |

Historical green runs on other SHAs are not current evidence.

## 4. Module verification state

### `server/`
Exact current-HEAD verification is **UNVERIFIED** pending fresh CI evidence. PR #104 added bounded rate-limit state and deterministic regression tests.

### `app/`
Exact current-HEAD verification is **UNVERIFIED** pending fresh CI evidence. Sentry integration lives on open branch for issue #7; the latest branch commit fixes the Kotlin DSL syntax for both BuildConfig provider expressions.

### `web/`
Exact current-HEAD verification is **UNVERIFIED** pending fresh CI evidence.

### `launcher/`
Dedicated test/coverage evidence is **UNVERIFIED**.

### `wow-addon/`
Dedicated test/coverage evidence is **UNVERIFIED**.

## 5. External activation state

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production `DATABASE_URL` and deployment secrets.
- Real-device acceptance before public distribution.
- Release tag and GitHub Release publication when chosen by Owner.
- Firebase Test Lab GCS `storage.objects.create` permission (issues #59/#62).
- Branch-protection required-status configuration remains an operator/governance concern unless independently verified.
- GitHub secret `SENTRY_DSN` (Owner must create before release builds emit Sentry events).

## 6. Explicit security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.

## 7. Authority

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.

## 8. Current workflow state

### PR #99 — workflow contract executor assignment — MERGED
Merged into `main` as `df05742ec609fd8e73576dc83ff10e86b2a82319`.

### PR #101 — docs hygiene / CURRENT_STATE sync — MERGED
Merged into `main` as `2098279cd7cdb9185e8f8ca24a2c95ef27719468`; historical documentation was archived and README canonical-state references were synchronized.

### PR #104 — bound and evict process-local rate-limit state — MERGED
Merged into `main` as `ab64505bb35d32006aa2c98940e807f3f9d87508`. Added bounded rate-limit state, inactive-bucket eviction and deterministic regression tests.

### PR #100 — CI state-sync enforcement — MERGED
Merged into `main` as `1df91de661c8bb0946d68f1671cbabf5f9714455`. State-sync gate + emulator runner pin.

### Issue #7 — Sentry Android observability — IN PROGRESS
Branch `feature/sentry-android-observability-7`, HEAD `fabaead06d740ceefb771bf17858f7f3b6578769`. The branch contains the Sentry Android SDK integration, privacy scrubbing, observability documentation, release-only `SENTRY_DSN` injection, and the Kotlin DSL syntax corrections for `SENTINEL_API_BASE_URL` and `SENTRY_DSN`. No merge performed by this work.

## 9. Open-work state

Open issues are backlog candidates, not automatic implementation instructions. Known external blockers include Firebase Test Lab IAM issues #59/#62.

Issue #7 remains in progress on the feature branch and requires CI/executor verification before Owner review. No merge or deploy was performed by this work.

## 10. Evidence discipline

For CI, tests and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED** rather than infer state from historical evidence.
