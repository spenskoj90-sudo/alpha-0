# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-23

## Canonical branch

**Canonical branch:** `main`

**Canonical HEAD:** `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79`  
**Tree:** `08a211e172cc835013194ee9adb6999f33ea2a1c`

**Latest accepted product change:** PR #46 — final Sentinel design system.

## Exact validation evidence

PR #46 exact-head commit: `43f94338df4da82917e615b2e1c9eb79014e9246`.

Exact-head CI evidence before merge:
- Security run `32626297508` / #170 — PASS.
- P1 Evidence run `32626297477` / #80 — PASS.
- ALPHA-0 Android CI run `32626297516` / #1022 — PASS.
- Build & Test run `32626297494` / #250 — all product/code/build jobs PASS; Firebase Test Lab job failed during Google Cloud authentication and did not execute instrumentation. This is the established FTL/GCP infrastructure exception.

The resulting merge commit is `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79`. The merge preserves the PR #46 tree. No claim is made that the pre-merge PR checks are separate post-merge runs for the merge SHA.

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
- Migration order is `001_initial.sql`, `002_p1_rls.sql`, `003_user_auth.sql`.
- `.github/workflows/p1-evidence.yml` currently uses `push.branches: [main]` and `pull_request.branches: [main]`.
- `.github/workflows/deploy.yml` currently triggers only on `release.published`.

## P0 / runtime findings

### P0 TCP bug — CLOSED AS ENVIRONMENTAL

The local plaintext-server BrokenPipeError was traced to aggressive battery/background-network restrictions on the user's device, not to an OkHttp/HTTPS/h2c client defect. The Android client uses `HttpURLConnection`. After battery optimization was disabled for the application, the first request completed immediately and the authenticated device flow continued. PR #34 added diagnostic exception reporting used to establish the runtime cause.

### Keystore / fingerprint

The Android identity implementation uses `AndroidKeyStore`, EC `secp256r1`, and `SHA256withECDSA`. The client derives the SHA-256 fingerprint from the encoded public key. Release fingerprint evidence was previously verified in CI; current product code retains the same Keystore-based identity model.

## OPEN / NOT ACCEPTED ITEMS

### PostgreSQL runtime persistence — OPEN

The schema and migration path are validated, but the runtime persistence path must still be demonstrated on current main before PostgreSQL is described as the authoritative runtime system of record.

### Recommendation authorization — OPEN SECURITY GAP

`POST /v1/recommendations` remains an authorization-review item until confirmed to call `policy_engine.authorize` with regression coverage.

### Repository hygiene — PARTIAL / OPEN

The explicitly audited stale branches were classified/cleaned to the extent supported by available tooling. Remaining work is classification of historical PRs/branches, ghost workflow records and duplicate state documents; destructive cleanup remains evidence-gated.

### Deploy workflow anomaly — OPEN INVESTIGATION

Current `.github/workflows/deploy.yml` contains only `release: types: [published]`. Direct current-file inspection shows no push trigger. The historical observation of push-associated Deploy runs is not yet attributed to a specific old workflow revision.

### Documentation consolidation — IN PROGRESS

This update synchronizes `TASKS.md`, `PROJECT_STATE.md`, `SENTINEL_CURRENT_STATE.md` and `README.md` with the post-PR #46 main state. Further cleanup of historical documents remains separate from product correctness.

## Workflow inventory

### Workflow files present on current main

- `.github/workflows/android-build.yml`
- `.github/workflows/build.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/p1-evidence.yml`
- `.github/workflows/release.yml`
- `.github/workflows/security.yml`

## Canonical state rules

- `main` is the only canonical product state.
- A branch, PR, local checkout, or historical AI report is not proof of current product state.
- A bare `PASS` is prohibited without exact-SHA evidence.
- Destructive repository cleanup requires direct verification and preservation of useful history.
- Every AI agent must record material work in the repository state/evidence documents.

## Authority

**Branch-state truth authority:** GPT / Final Integrator.  
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.