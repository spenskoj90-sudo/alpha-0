# SENTINEL — Canonical Current State

**State record:** 2026-09-02  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `a261389f589c0d281c3f45a772fa6ee17abade42`  
**Current product change on main:** PR #115 — feat(api): characters/game-state Phase 1 MVP (merged)

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
- **Characters/game-state Phase 1 (PR #115):** store `list_characters` / `get_character` / `upsert_character`; read routes `GET /v1/characters`, `/v1/characters/{id}`, `/v1/games`, `/v1/games/{id}`, `/v1/games/{id}/access` with auth + IDOR. Event→character projection is Phase 2.

## 2. Exact-HEAD evidence

Current `main` HEAD is `a261389f589c0d281c3f45a772fa6ee17abade42`, the merge commit for PR #115.

Product CI for this SHA (push to main):

| Workflow | Run ID | Conclusion |
|----------|--------|------------|
| Build & Test | [33599398555](https://github.com/spenskoj90-sudo/alpha-0/actions/runs/33599398555) | success |
| Security | [33599398765](https://github.com/spenskoj90-sudo/alpha-0/actions/runs/33599398765) | success |
| ALPHA-0 Android CI | [33599398549](https://github.com/spenskoj90-sudo/alpha-0/actions/runs/33599398549) | success |
| P1 Evidence | [33599398550](https://github.com/spenskoj90-sudo/alpha-0/actions/runs/33599398550) | success |
| Release Candidate Artifact | [33599398607](https://github.com/spenskoj90-sudo/alpha-0/actions/runs/33599398607) | success |
| Deploy | [33599397558](https://github.com/spenskoj90-sudo/alpha-0/actions/runs/33599397558) | failure (expected without DEPLOY_* secrets) |

Numeric coverage remains **UNVERIFIED** as a published percent until extracted from Build & Test artifacts for this HEAD.

## 3. Module verification state

### `server/`
Rate-limit bounding/eviction is merged in PR #104. Security-negative, RLS, and postgres refresh concurrency coverage exist under `server/tests/`. Character store methods and game-state read routes merged in PR #115; tests in `test_game_state.py`.

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

## 5. Explicit security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.

## 6. Completed workflow state

- **Issue #22 — repository governance: COMPLETE (2026-09-01).** Historical branch cleanup (D-016/D-017) and Owner-configured required status checks on `main` (D-018).
- **Issue #63 — P1 preventive hardening: COMPLETE (2026-09-01).** Closed by Owner after D-019/D-020.
- **PR #115 — characters/game-state Phase 1 MVP: COMPLETE / MERGED.** `a261389f589c0d281c3f45a772fa6ee17abade42`.
- **PR #114 / #113 / #112 / #111 / #110 / #109 / #105 / #104 / #100 / #101 / #103 / #108** — as previously recorded.

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
| 2 Android lifecycle/session tests | Partial | `SecureSessionStorePersistenceTest`, `SessionManagerInstrumentedTest`, `AuthApiRefreshInstrumentedTest`; deeper process-death + revoke residual |
| 3 Client refresh-token lifecycle | Done | PR #96 |
| 4 Bound/evict rate-limit | Done | PR #104 |
| 5 FTL instrumentation expansion | Blocked | #59; routine CI uses emulator (D-013) |
| 6 Web/admin security regressions | Minimal done | `route.test.ts` entitlements (PR #92 lineage) |
| 7 Schema-domain reconciliation | Phase 1 done | #107 / PR #115; Phase 2 projection remains |

**Closed by Owner 2026-09-01.** Residual optional (deeper IDOR, Android process-death/revoke) left out of scope.

## 9. Open work

- **#107** — characters/game-state domain **Phase 1 COMPLETE** on main (PR #115). **Phase 2** remains: event → character projection (ARCHITECTURE_V4 §5–6); no direct public character write API.
- **#59** — FTL IAM (external; optional given emulator CI).
- **#13, #11, #10, #8** — backlog unless approved.

## 10. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED**.

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.
