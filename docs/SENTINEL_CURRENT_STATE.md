# SENTINEL — Canonical Current State

**State record:** 2026-09-01  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `516c53862ee3fbf715f5891495f74d9127b13026`  
**Current product change on main:** PR #112 — docs: historical branch hygiene complete (merged)

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

Current `main` HEAD is `516c53862ee3fbf715f5891495f74d9127b13026`, the merge commit for PR #112.

Product CI claims for this SHA should be verified independently via Actions for workflows Build & Test, Security, ALPHA-0 Android CI, and P1 Evidence. Deploy remains expected-failure without external DEPLOY_* secrets.

Numeric coverage remains **UNVERIFIED** until a completed Build & Test run ID for this HEAD is independently confirmed.

## 3. Module verification state

### `server/`
Rate-limit bounding/eviction is merged in PR #104. Security-negative, RLS, and postgres refresh concurrency coverage exist under `server/tests/`.

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
- **PR #112 — docs: historical branch hygiene complete: COMPLETE / MERGED.** `516c53862ee3fbf715f5891495f74d9127b13026`.
- **PR #111 / #110 / #109 / #105 / #104 / #100 / #101 / #103 / #108** — as previously recorded.

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

## 8. Issue #63 reconciliation (2026-09-01)

| Backlog item | Status | Evidence on main |
|--------------|--------|------------------|
| 1 PostgreSQL security-negative / concurrent refresh | Mostly done | `test_security_negative.py`, `test_rls_policies.py`, `test_postgres_refresh_concurrency.py`, `test_service_role_boundary.py` |
| 2 Android lifecycle/session tests | Partial | `SecureSessionStorePersistenceTest`, `SessionManagerInstrumentedTest`, `AuthApiRefreshInstrumentedTest`; deeper process-death + revoke residual |
| 3 Client refresh-token lifecycle | Done | PR #96 |
| 4 Bound/evict rate-limit | Done | PR #104 |
| 5 FTL instrumentation expansion | Blocked | #59; routine CI uses emulator (D-013) |
| 6 Web/admin security regressions | Minimal done | `route.test.ts` entitlements (PR #92 lineage) |
| 7 Schema-domain reconciliation | Moved | #107 |

Residual under #63 only if Owner wants more IDOR depth or Android process-death/revoke tests; otherwise #63 may be closed as substantially complete.

## 9. Open work

- **#107** — characters/game-state domain (planning; needs intake).
- **#59** — FTL IAM (external; optional given emulator CI).
- **#63** — residual optional (see §8).
- **#13, #11, #10, #8** — backlog unless approved.

## 10. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED**.

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.
