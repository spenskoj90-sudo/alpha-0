# SENTINEL — Canonical Current State

**State record:** 2026-09-05  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Observed `main` HEAD (snapshot):** `410ff49d5ad8974e29fbce50cb24dc9a9a06e388`  
**Current process state:** Issue #134 / PR #135 — GPT-primary engineering workflow and direct repository inspection — **MERGED/COMPLETE**. `main` remains authoritative for product and process state; the observed SHA above is a snapshot and must not be treated as the live HEAD after subsequent merges.

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
- **Characters/game-state domain (#107) COMPLETE on main:**
  - Phase 1 (PR #115): store `list_characters` / `get_character` / `upsert_character`; read routes `GET /v1/characters`, `/v1/characters/{id}`, `/v1/games`, `/v1/games/{id}`, `/v1/games/{id}/access` with auth + IDOR.
  - Phase 2 (PR #118): `character_projection.py` + `apply_character_projections` after successful `/v1/events:batch`; types `character.snapshot` / `character.upsert` / `character.state`; required payload `game_id`, `external_id`, `name`; invalid payload skips projection. No public mutable character write API.
- **Deploy workflow:** PR #120 changed `deploy.yml` to run only on published GitHub Releases or manual `workflow_dispatch`. Optional remote rollout is gated by repository variable `DEPLOY_ENABLED=true`; deploy secrets are checked only inside the job when enabled. No routine push-to-main Deploy run is expected.

## 2. Exact-HEAD evidence

The observed `main` HEAD for this snapshot is `2553270da1c07e82304b232ebc401781920efa64`, the merge commit for PR #147. The available GitHub PR-triggered workflow-run lookup for this exact SHA currently returns no runs. Therefore exact-SHA CI/release status is **UNVERIFIED** unless a required run is independently verified against this exact SHA.

PR #135 was independently checked by the Human Owner before merge; that evidence applied to the exact PR head `a049e08b80ac00378f48116ebf998a54c416a538`, not to the subsequent squash merge SHA.

PR #147 (`ci: auto-sync CURRENT_STATE HEAD via PR (no direct push to main)`) is **MERGED**. It provides a future synchronization mechanism by creating a PR when the recorded CURRENT_STATE HEAD differs from the live push SHA; it does not make the snapshot SHA above a permanent live-HEAD claim.

Previously recorded CI runs for predecessor SHA `f5b342310a0278b318b434976cc0d33e15fe10a6` were:

| Workflow | Run | Conclusion |
|----------|-----|------------|
| Build & Test | #432 on `f5b3423` | success |
| Security | #349 on `f5b3423` | success |
| ALPHA-0 Android CI | #1498 on `f5b3423` | success |
| P1 Evidence | #257 on `f5b3423` | success |
| Release Candidate Artifact | #32 on `f5b3423` | success |

Those predecessor runs are historical evidence only and do not establish CI status for `2553270da1c07e82304b232ebc401781920efa64`.

Numeric coverage remains **UNVERIFIED** as a published percent until extracted from the relevant Build & Test artifact for the exact HEAD under review.

## 3. Module verification state

### `server/`
Rate-limit bounding/eviction is merged in PR #104. Security-negative, RLS, and postgres refresh concurrency coverage exist under `server/tests/`. Character store + game-state read routes (PR #115, `test_game_state.py`). Event→character projection (PR #118, `character_projection.py`, `test_character_projection.py`).

### `app/`
Sentry Android runtime observability is merged in PR #105. Client refresh lifecycle and session persistence tests exist (PR #94/#96 lineage).

### `web/`
Admin entitlements route test present (`web/app/api/admin/entitlements/route.test.ts`).

### `launcher/` / `wow-addon/`
Dedicated test/coverage evidence: **UNVERIFIED**.

## 4. External activation state

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production database: Supabase (secret configured).
- Real-device acceptance before public distribution.
- Release tag and GitHub Release publication when chosen by Owner.
- Firebase Test Lab GCS `storage.objects.create` permission (issue #59).
- GitHub repository secret `SENTRY_DSN` before release builds emit Sentry events.
- Optional remote Deploy: set repository variable `DEPLOY_ENABLED=true` and secrets `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_KEY` only when a host is ready.

## 5. Explicit security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.

## 6. Completed workflow and product state

- **Issue #22 — repository governance: COMPLETE (2026-09-01).** Historical branch cleanup (D-016/D-017) and Owner-configured required status checks on `main` (D-018).
- **Issue #63 — P1 preventive hardening: COMPLETE (2026-09-01).** Closed by Owner after D-019/D-020.
- **Issue #107 — characters/game-state domain: COMPLETE (2026-09-02).** Phase 1 PR #115; Phase 2 PR #118 at `f5b342310a0278b318b434976cc0d33e15fe10a6`.
- **PR #120 — Deploy workflow trigger fix + docs synchronization: MERGED.** Main subsequently advanced through PR #10 and then PR #135.
- **Issue #134 — GPT-primary engineering workflow: COMPLETE (2026-09-04).** Documentation-only PR #135 merged as squash commit `e1be60e482ea22100f81081c0effbe278b19e21c`. The workflow and responsibility model are now canonical.
- **Issue #136 — post-merge current-state synchronization: COMPLETE.** PR #137 merged as commit `10b6c3186d792d9c892e5ca086b40ef99a16640e`.
- **Issue #146 — CURRENT_STATE self-staleness: IN PROGRESS.** This snapshot records the observed post-PR-#147 main state and explicitly separates that observation from the live `main` HEAD.
- **PR #147 — auto-sync CURRENT_STATE HEAD via PR: MERGED.** Future synchronization is performed through a PR rather than a direct push to `main`.

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

## 8. Issue #63 reconciliation (closed 2026-09-01)

| Backlog item | Status | Evidence on main |
|--------------|--------|------------------|
| 1 PostgreSQL security-negative / concurrent refresh | Mostly done | `test_security_negative.py`, `test_rls_policies.py`, `test_postgres_refresh_concurrency.py`, `test_service_role_boundary.py` |
| 2 Android lifecycle/session tests | Partial | residual optional out of scope |
| 3 Client refresh-token lifecycle | Done | PR #96 |
| 4 Bound/evict rate-limit | Done | PR #104 |
| 5 FTL instrumentation expansion | Blocked | #59; emulator CI (D-013) |
| 6 Web/admin security regressions | Minimal done | `route.test.ts` |
| 7 Schema-domain reconciliation | Done | #107 / PR #115 + #118 |

## 9. Open work

- **#59** — FTL IAM (external; optional given emulator CI).
- **#13** — define PostHog telemetry contract.
- **#11** — synchronize Figma design system with implementation.
- **#10** — establish measurable build/runtime performance baseline.

Issue #8 (SENTINEL baseline consistency audit) is **CLOSED**; its completed audit was recorded through PRs #106/#108. Issue #107 is **CLOSED** as the completed characters/game-state domain.

## 10. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED**.

## 11. Engineering responsibility model

| Responsibility | GPT / ChatGPT | Grok | Human Owner |
|---|---|---|---|
| Repository inspection | Primary | When delegated | Final visibility/authority |
| Normal implementation | Primary | Not default | Scope/acceptance authority |
| Architecture and technical decisions | Primary | Consulted/implemented when delegated | Final product authority |
| Large-scale exceptional implementation | May lead; may delegate | Secondary executor | Approves scope/delegation |
| Tests / CI / evidence analysis | Primary | Required for delegated work | Independently verifies merge gate |
| Documentation synchronization | Primary | Required when delegated work changes state | Final acceptance |
| Merge to `main` | Propose only | Propose only | **Exclusive** |
| Deploy | Propose only | Propose only | **Exclusive** |
| Credentials / secrets / signing material | No access | No access | **Exclusive** |
| Release tags/releases | Propose only | Propose only | **Exclusive** |
| Branch protection | Propose only | Propose only | **Exclusive** |

GPT's direct GitHub connector access is an engineering capability, not an elevation of authority. It permits repository inspection and approved scoped changes but does not permit access to protected secret contents or Owner-only actions.

**Final Integrator:** GPT / ChatGPT.  
**Primary Executor:** GPT / ChatGPT.  
**Exceptional Secondary Executor:** Grok.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, protected repository actions, and destructive cleanup.
