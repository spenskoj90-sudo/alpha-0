# SENTINEL — Audit Reconciliation

**Date:** 2026-08-25  
**Baseline:** `209fd63f0bcd0f897ee257cd79d33a12479ccfd9`  
**Audits reconciled:** Grok full repository audit + DeepSeek full system QA/security/architecture audit  
**Mode:** evidence-first; no finding is treated as a bug until verified against the current repository.

## 1. Executive result

The two external audits are **not equivalent sources of truth**. Grok largely matches the current repository architecture. DeepSeek contains several findings that refer to a different Kotlin/Ktor repository layout and therefore are not applicable to the current `alpha-0` baseline.

The current backend is Python/FastAPI with SQLAlchemy/PostgreSQL and a MemoryStore test/dev implementation. The Android client is Kotlin/Compose. The canonical FTL workflow is `.github/workflows/build.yml`.

## 2. Confirmed findings

### P0 — FTL infrastructure blocker

Firebase Test Lab reaches authentication, gcloud setup, model discovery, and artifact resolution, then fails on GCS `storage.objects.create` for the Test Lab bucket. APK artifact paths are already correct and must not be changed again.

**Owner action:** grant the Firebase Test Lab service account the minimum bucket-scoped permission required to create Test Lab objects. Tracked in GitHub issue #59.

### P1/P2 — process-local rate limiter

`server/app/main.py` contains an active rate limiter for auth/device operations. It is implemented as an in-process dictionary/deque and therefore does not provide a global limit across multiple API replicas.

**Classification:** confirmed scaling hardening, not an immediate authentication bypass. Keep for MVP; replace with a distributed limiter when horizontal scaling is introduced.

### P1/P2 — dual store architecture

`server/app/core/store.py` contains both `MemoryStore` and `PostgresStore`. Some lifecycle SQL helpers also live in `server/app/main.py`.

**Classification:** confirmed architectural debt / behavioral-drift risk. Do not rewrite during the FTL incident fix.

### P1/P2 — Android synchronous networking

`app/src/main/java/com/alpha0/app/auth/AuthApi.kt` uses synchronous `HttpURLConnection` calls. This is a real ANR/reliability risk if invoked from the UI thread. It should be migrated to a coroutine-based network layer before production-scale feature growth.

### P1/P2 — Android session lifecycle gaps

`MainActivity` derives navigation from an initially loaded session and there is no visible client refresh path in `AuthApi`. Process-death/session-expiry behavior therefore needs explicit lifecycle tests and a refresh-capable client layer.

### P1 — Postgres security-test parity

The CI separates memory/core tests from `pytest -m postgres`. Critical security-negative tests must be identified and duplicated/marked for PostgreSQL where persistence, RLS, constraints, or transactions can change behavior.

## 3. Findings rejected as false positives / wrong repository

### DeepSeek SEC-001 — hardcoded JWT secret

Not applicable. The current server issues opaque random access/refresh tokens and stores hashes; it is not using the claimed Kotlin/Ktor `application.conf` JWT-secret architecture.

### DeepSeek SEC-002 — Android backup enabled

False. Current `AndroidManifest.xml` explicitly sets `android:allowBackup="false"`.

### DeepSeek SEC-003 — missing auth rate limiting

False as stated. Current `main.py` calls the active `RateLimiter` for auth registration/login and device operations. The real issue is process-local scope, not absence of rate limiting.

### DeepSeek Kotlin/Ktor BUG-001/002/003 and related paths

Not applicable. Paths such as `server/src/main/kotlin/...`, `DeviceRegistration.kt`, `DeviceRevoke.kt`, `KeystoreManager.kt`, and the claimed Ktor application configuration do not describe the current repository architecture.

### Grok duplicate GET `/v1/devices/{device_id}`

Not confirmed. The current main route is `/v1/devices/{device_id}` while `wow_api.py` exposes `/v1/devices/me`; these are distinct paths. The real concern is module coupling where `wow_api.py` imports security/store helpers from `app.main`.

### DeepSeek missing security headers

False for the Core API. `server/app/main.py` already adds X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy and CSP headers.

## 4. Findings requiring verification before modification

1. Device-registration uniqueness/constraint behavior under concurrent requests.
2. PostgreSQL RLS and service-role semantics for all security-sensitive routes.
3. Refresh/revoke lifecycle under concurrency and after process restart.
4. Android Keystore loss/alias rotation behavior.
5. Web security headers and admin-token handling at the actual deployed boundary.
6. Branch protection / required status checks through repository settings.
7. Foreign-device authorization negatives against PostgreSQL, not only MemoryStore.
8. Database foreign-key indexes and query plans before adding indexes speculatively.

## 5. Explicit non-actions

Do **not**:

- add a second FTL job;
- change the verified Android artifact paths;
- rotate the release certificate/fingerprint without a coordinated key-rotation plan;
- replace the current token architecture with JWT based on the DeepSeek finding;
- delete `android-build.yml` without an explicit workflow-policy decision;
- introduce Redis/microservices/soft-delete solely because an audit suggested future scaling work;
- treat CI success as proof of production source-of-record correctness.

## 6. Engineering order

1. Resolve FTL GCS IAM and verify one Build & Test run.
2. Configure required GitHub status checks at repository settings level.
3. Add/port critical security-negative tests to PostgreSQL.
4. Harden Android network/session lifecycle before the next major feature wave.
5. Consolidate store/lifecycle seams incrementally with regression tests.
6. Expand instrumentation coverage after FTL is operational.
7. Revisit distributed rate limiting only when horizontal scaling becomes real.

## 7. Evidence rule

Every future audit finding must be classified as one of:

- **CONFIRMED — FIX NOW**
- **CONFIRMED — FIX LATER**
- **NEEDS VERIFICATION**
- **FALSE POSITIVE / NOT APPLICABLE**

No repository modification should be justified by an unverified finding alone.
