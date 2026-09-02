# SENTINEL — Canonical Current State

**State record:** 2026-09-02  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `f5b342310a0278b318b434976cc0d33e15fe10a6`  
**Current product change on main:** PR #118 — #107 Phase 2 event→character projection (merged)

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
- **Characters/game-state Phase 1 (PR #115):** store `list_characters` / `get_character` / `upsert_character`; read routes `GET /v1/characters`, `/v1/characters/{id}`, `/v1/games`, `/v1/games/{id}`, `/v1/games/{id}/access` with auth + IDOR.
- **Characters/game-state Phase 2 (PR #118):** `character_projection.py` + `apply_character_projections` after successful `/v1/events:batch`; types `character.snapshot` / `character.upsert` / `character.state`; required payload `game_id`, `external_id`, `name`; invalid payload skips projection (batch still accepted). No public mutable character write API.

## 2. Exact-HEAD evidence

Current `main` HEAD is `f5b342310a0278b318b434976cc0d33e15fe10a6`, the merge commit for PR #118.

Product CI for this SHA (push to main after #118):

| Workflow | Conclusion | Notes |
|----------|------------|-------|
| Build & Test | success | run series after #118 merge |
| Security | success | |
| ALPHA-0 Android CI | success | |
| P1 Evidence | success | |
| Release Candidate Artifact | success | |
| Deploy | **was** failure | Invalid workflow: `secrets` in job-level `if` (fixed in follow-up PR; not a product defect) |

Numeric coverage remains **UNVERIFIED** as a published percent until extracted from Build & Test artifacts for this HEAD.

## 3. Module verification state

### `server/`
Rate-limit bounding/eviction is merged in PR #104. Security-negative, RLS, and postgres refresh concurrency coverage exist under `server/tests/`. Character store methods and game-state read routes merged in PR #115 (`test_game_state.py`). Phase 2 projection + tests merged in PR #118 (`character_projection.py`, `test_character_projection.py`).

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
- Optional remote deploy (`DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_KEY`) — unset is intentional until Owner configures production host.

## 5. Explicit security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.

## 6. Completed workflow state

- **Issue #22 — repository governance: COMPLETE (2026-09-01).** Historical branch cleanup (D-016/D-017) and Owner-configured required status checks on `main` (D-018).
- **Issue #63 — P1 preventive hardening: COMPLETE (2026-09-01).** Closed by Owner after D-019/D-020.
- **Issue #107 — characters/game-state domain: COMPLETE (2026-09-02).** Phase 1 PR #115 + Phase 2 PR #118 at `f5b342310a0278b318b434976cc0d33e15fe10a6`.
- **PR #118 / #116 / #115 / #114 / #113 / #112 / #111 / #110 / #109 / #105 / #104 / #100 / #101 / #103 / #108** — as previously recorded.

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
| 7 Schema-domain reconciliation | Done | #107 / PR #115 + PR #118 |

**Closed by Owner 2026-09-01.** Residual optional (deeper IDOR, Android process-death/revoke) left out of scope.

## 9. Open work

- **#59** — FTL IAM (external; optional given emulator CI).
- **#13, #11, #10, #8** — backlog unless approved.

## 10. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED**.

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.
