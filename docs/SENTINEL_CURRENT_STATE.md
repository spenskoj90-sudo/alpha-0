# SENTINEL — Canonical Current State

**State record:** 2026-09-06  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Observed `main` HEAD (snapshot):** `2553270da1c07e82304b232ebc401781920efa64`  
**Current process state:** Sentry Android runtime path **VERIFIED** on physical device (Owner evidence: `SENTINEL_SENTRY_SMOKE`, issue 145252132, release 1.0.0-RC2). TEMP smoke UI removed after confirm. Live `main` HEAD may be ahead of the observed snapshot; auto-sync advances that line.

> Git/main is authoritative for product state. Unmerged branch evidence is not current product state unless merged.
> This document records an observed/snapshot `main` SHA; the live `main` HEAD may advance after this snapshot is committed.
> Exact CI/release claims require the exact SHA plus workflow Run ID; unresolved evidence is recorded as **UNVERIFIED**.
> GPT/ChatGPT is the primary SENTINEL executor and final integrator. Grok is a secondary executor for exceptional, genuinely large-scale work. Human Owner remains final authority for protected actions and final acceptance.

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
- **Sentry runtime path VERIFIED (2026-09-06):** Owner physical device (Infinix / Android 14) release `1.0.0-RC2` produced event `SENTINEL_SENTRY_SMOKE` in org `sentinel-p7` (issue 145252132), stack `SentrySmoke.captureSmoke` ← LoginScreen. TEMP smoke helper/UI removed after confirmation; permanent path remains `SentinelApplication` init + scrubbing only.
- **Characters/game-state domain (#107) COMPLETE on main:**
  - Phase 1 (PR #115): store `list_characters` / `get_character` / `upsert_character`; read routes `GET /v1/characters`, `/v1/characters/{id}`, `/v1/games`, `/v1/games/{id}`, `/v1/games/{id}/access` with auth + IDOR.
  - Phase 2 (PR #118): `character_projection.py` + `apply_character_projections` after successful `/v1/events:batch`; types `character.snapshot` / `character.upsert` / `character.state`; required payload `game_id`, `external_id`, `name`; invalid payload skips projection. No public mutable character write API.
- **Deploy workflow:** PR #120 changed `deploy.yml` to run only on published GitHub Releases or manual `workflow_dispatch`. Optional remote rollout is gated by repository variable `DEPLOY_ENABLED=true`; deploy secrets are checked only inside the job when enabled. No routine push-to-main Deploy run is expected.
- **Auto-sync CURRENT_STATE CI (Issue #154):** Required workflows (`build.yml`, `security.yml`, `p1-evidence.yml`) also trigger on `push` to `ci/state-sync-auto-*`. The sync commit no longer uses `[skip ci]`. Code path is on main via PR #155–#158.

## 2. Exact-HEAD evidence

The observed `main` HEAD for this snapshot is `2553270da1c07e82304b232ebc401781920efa64`, the merge commit for PR #147. Live `main` advanced through Sentry smoke PRs #159/#161; exact CI for those SHAs must be claimed with SHA + Run ID only.

## 3. Module verification state

### `server/`
Rate-limit bounding/eviction is merged in PR #104. Security-negative, RLS, and postgres refresh concurrency coverage exist under `server/tests/`. Character store + game-state read routes (PR #115). Event→character projection (PR #118).

### `app/`
Sentry Android runtime observability is merged in PR #105 and **runtime-verified** on device (2026-09-06). Client refresh lifecycle and session persistence tests exist (PR #94/#96 lineage). TEMP smoke UI removed after Owner confirm.

### `web/`
Admin entitlements route test present (`web/app/api/admin/entitlements/route.test.ts`).

### `launcher/` / `wow-addon/`
Dedicated test/coverage evidence: **UNVERIFIED**.

## 4. External activation state

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production database: Supabase (secret configured).
- Real-device acceptance before public distribution (partial: Sentry path verified on one physical device).
- Release tag and GitHub Release publication when chosen by Owner.
- Firebase Test Lab GCS `storage.objects.create` permission (issue #59).
- GitHub repository secret `SENTRY_DSN`: **active**; end-to-end event confirmed in Sentry project `android` / org `sentinel-p7`.
- Optional remote Deploy: set repository variable `DEPLOY_ENABLED=true` and secrets `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_KEY` only when a host is ready.
- `SENTINEL_API_BASE_URL` is **not** injected by Release Candidate CI; release APK defaults to `http://127.0.0.1:8000`. Physical-device login against production Core remains **BLOCKED** until a reachable base URL is configured and APK rebuilt.

## 5. Explicit security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.

## 6. Completed workflow and product state

- **Issue #22 — repository governance: COMPLETE (2026-09-01).**
- **Issue #63 — P1 preventive hardening: COMPLETE (2026-09-01).**
- **Issue #107 — characters/game-state domain: COMPLETE (2026-09-02).**
- **Issue #7 — Sentry Android observability: runtime path VERIFIED (2026-09-06)** after Owner device event; TEMP smoke removed.
- **Issue #134 — GPT-primary engineering workflow: COMPLETE (2026-09-04).**
- **PR #147 / Issue #154 — CURRENT_STATE auto-sync via PR + required checks: code on main.**

## 7. Branch protection (issue #22) — Owner configured 2026-09-01

Required status checks on `main` (job names as shown in GitHub UI):

- Secret and image scan
- Core tests and coverage
- Android build and tests
- Dependency audit
- Web build
- CodeQL
- Build Android APK
- P1 evidence artifacts
- PostgreSQL integration and recovery
- Repository verification

Also enabled: require branches up to date before merging. Deploy is intentionally **not** required.

## 8. Open work

- **#59** — FTL IAM (external; optional given emulator CI).
- **#13** — define PostHog telemetry contract.
- **#11** — synchronize Figma design system with implementation.
- **#10** — establish measurable build/runtime performance baseline.
- **SENTINEL_API_BASE_URL for release** — inject reachable production/staging URL into release assemble when Core is available.
- **PR #133** — Master Architecture v0.3 DRAFT (Owner review).

## 9. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED**.

## 10. Engineering responsibility model

| Responsibility | GPT / ChatGPT | Grok | Human Owner |
|---|---|---|---|
| Repository inspection | Primary | When delegated | Final visibility/authority |
| Normal implementation | Primary | Not default | Scope/acceptance authority |
| Architecture and technical decisions | Primary | Consulted/implemented when delegated | Final product authority |
| Large-scale exceptional implementation | May lead; may delegate | Secondary executor | Approves scope/delegation |
| Tests / CI / evidence analysis | Primary | Required for delegated work | Independently verifies merge gate |
| Documentation synchronization | Primary | Required when delegated work changes state | Final acceptance |
| Merge to `main` | Propose only | Propose only | **Exclusive** (Owner may explicitly delegate merge of a green PR) |
| Deploy | Propose only | Propose only | **Exclusive** |
| Credentials / secrets / signing material | No access | No access | **Exclusive** |
| Release tags/releases | Propose only | Propose only | **Exclusive** |
| Branch protection | Propose only | Propose only | **Exclusive** |

**Final Integrator:** GPT / ChatGPT.  
**Primary Executor:** GPT / ChatGPT.  
**Exceptional Secondary Executor:** Grok.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, protected repository actions, and destructive cleanup.
