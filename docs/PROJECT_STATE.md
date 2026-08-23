# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-23

## Canonical branch

**Canonical branch:** `main`

**Canonical HEAD:** `9f724089fc01d8aeef247166ec9de2fbf54202d3`
**Tree:** product tree from PR #46 plus subsequent documentation and onboarding changes.

**Latest accepted product change:** PR #51 — battery optimization onboarding.
**Latest accepted documentation change:** PR #50 — post-PR #49 production-readiness state synchronization.

## Exact validation evidence

PR #46 exact-head commit: `43f94338df4da82917e615b2e1c9eb79014e9246`.

Exact-head CI evidence before merge:
- Security run `32626297508` / #170 — PASS.
- P1 Evidence run `32626297477` / #80 — PASS.
- ALPHA-0 Android CI run `32626297516` / #1022 — PASS.
- Build & Test run `32626297494` / #250 — all product/code/build jobs PASS; Firebase Test Lab job failed during Google Cloud authentication and did not execute instrumentation. This is the established FTL/GCP infrastructure exception.

The resulting merge commit is `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79`.
PR #47 synchronized canonical state documentation.
PR #49 was a documentation-only follow-up; Build & Test `32629034760` had all product/code/build jobs PASS and only the Firebase Test Lab authentication step failed with the known GCP configuration exception.
PR #51 added optional Android battery-optimization onboarding and merged as `9f724089fc01d8aeef247166ec9de2fbf54202d3`.

## Current repository facts

### CURRENT / VERIFIED ON MAIN

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Android Keystore-based device identity exists; public fingerprint/DER are exposed for binding while private key material remains in Android Keystore.
- Login/Register are implemented in `LoginScreen` register mode.
- Complete Android MVP navigation is implemented: Login/Register → Device Setup → Dashboard → Device Details → Game Details.
- Dashboard, Device Details and Game Details use authenticated backend APIs rather than the former placeholder.
- Authenticated device and entitlement read APIs exist.
- Device rotate/revoke endpoints exist and are canonical in `server/app/main.py`; duplicate routes were removed from `wow_api.py`.
- `/v1/devices/bind` binds the authenticated session to the device.
- Session/device lifecycle security regression coverage exists in `server/tests/test_device_session_lifecycle.py`.
- Final Sentinel design system is merged: centralized colors, Outfit/Inter/JetBrains Mono typography, 4dp cards with 2dp ultraviolet left accent, status badges, primary/destructive controls, and one-shot 1000ms scan-line on the two specified device-status cards.
- Device Setup now contains optional battery-optimization guidance backed by `BatteryOptimization`, with state refresh on lifecycle resume; this addresses the previously verified device-specific background-network failure mode without changing the bind flow.
- Migration order is `001_initial.sql`, `002_p1_rls.sql`, `003_user_auth.sql`.
- `.github/workflows/p1-evidence.yml` currently uses `push.branches: [main]` and `pull_request.branches: [main]`.
- `.github/workflows/deploy.yml` currently triggers only on `release.published` in the checked-in file.
- `POST /v1/recommendations` calls `authorize_request` with action `knowledge:recommend`; a direct unauthorized regression test is present in `server/tests/test_security_negative.py` and expects HTTP 403 without the required `game:read` scope.

## P0 / runtime findings

### P0 TCP bug — CLOSED AS ENVIRONMENTAL

The local plaintext-server BrokenPipeError was traced to aggressive battery/background-network restrictions on the user's device, not to an OkHttp/HTTPS/h2c client defect. The Android client uses `HttpURLConnection`. After battery optimization was disabled for the application, the first request completed immediately and the authenticated device flow continued. PR #34 added diagnostic exception reporting used to establish the runtime cause.

### Keystore / fingerprint

The Android identity implementation uses `AndroidKeyStore`, EC `secp256r1`, and `SHA256withECDSA`. The client derives the SHA-256 fingerprint from the encoded public key. Release fingerprint evidence was previously verified in CI; current product code retains the same Keystore-based identity model.

## CI governance

### Protected main — VERIFIED

`main` is protected according to live repository branch metadata.

### Required status-check contexts — VERIFIED EMPTY / OPEN GOVERNANCE GAP

Live branch metadata exposes the protection payload: `required_status_checks.enforcement_level = non_admins`, but both `contexts` and `checks` are empty. Therefore no named required status-check context is currently configured for protected `main`.

This is a real process risk: GitHub branch protection is enabled, but the repository is not currently enforcing the project's intended CI acceptance checks through named required contexts. The internal Evidence Protocol remains mandatory, but it is not equivalent to a GitHub-enforced merge gate.

Recommended normal merge-gate contexts are the stable non-FTL product/security checks. Firebase Test Lab remains a documented infrastructure exception and should not be the sole merge blocker.

## OPEN / NOT ACCEPTED ITEMS

### PostgreSQL runtime persistence — OPEN

The application selects `PostgresStore(DATABASE_URL)` when `DATABASE_URL` is set, and production startup rejects a missing `DATABASE_URL`. The `/healthz` path also performs `SELECT 1` when the active store is PostgreSQL. This proves the application-side runtime path and production guard, but not that the currently deployed runtime actually has PostgreSQL configured and authoritative. Runtime proof remains open until an exact-main environment/deployment evidence bundle is captured.

### CI governance required checks — OPEN

Live repository metadata confirms the required-check arrays are empty. The owner must configure the intended required status checks/ruleset in GitHub Settings/Rulesets. Until that administrative change is made and independently verified, the merge gate remains process-controlled rather than GitHub-enforced.

### Real-device battery onboarding verification — OPEN MANUAL ACCEPTANCE

PR #51 and its product CI evidence establish build/test acceptance. A physical Android device still needs to verify that the Device Setup action opens the appropriate system settings, that returning to the app refreshes the state, and that the onboarding does not interfere with the existing bind flow.

### Repository hygiene — PARTIAL / OPEN

Remaining work is classification of historical PRs/branches, ghost workflow records and duplicate state documents; destructive cleanup remains evidence-gated and is intentionally deferred while product readiness is prioritized.

### Deploy workflow anomaly — OPEN INVESTIGATION

Current `.github/workflows/deploy.yml` contains only `release: types: [published]`. Direct current-file inspection shows no push trigger. Historical observation of push-associated Deploy failures is not yet attributed to a specific old workflow revision. Do not change the release trigger solely to silence historical runs.

### Documentation consolidation — IN PROGRESS

Canonical HEAD, PR #49 evidence, PR #51 evidence, and CI governance state are recorded here. Historical documents remain separate until classified.

## Workflow inventory

### Workflow files present on current main

- `.github/workflows/android-build.yml`
- `.github/workflows/build.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/p1-evidence.yml`
- `.github/workflows/release.yml`
- `.github/workflows/security.yml`

### Historical / ghost workflow names observed in Actions UI

Grok's live audit recorded `fingerprint-diagnostic.yml`, `sentinel-backend-ci.yml`, and `codeql.yml` as visible in Actions despite not being present in the current workflow tree. This remains a hygiene investigation item; no destructive workflow cleanup was performed without direct history verification.

## Canonical state rules

- `main` is the only canonical product state.
- A branch, PR, local checkout, or historical AI report is not proof of current product state.
- A bare `PASS` is prohibited without exact-SHA evidence.
- Destructive repository cleanup requires direct verification and preservation of useful history.
- Every AI agent must record material work in the repository state/evidence documents.

## Authority

**Branch-state truth authority:** GPT / Final Integrator.
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
