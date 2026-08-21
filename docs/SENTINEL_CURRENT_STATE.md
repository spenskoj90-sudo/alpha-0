# SENTINEL — Canonical Current State

**State record:** 2026-08-21  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD:** `4a0fd8255e4b7beb065e73a254ebb72d3b8b4d11`

> This document is repository-grounded. It separates current `main` implementation from architecture, branch-only work, historical evidence, and unverified AI claims.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. `VERIFIED` requires the seven-part evidence bundle: exact SHA, main-line reachability, relevant implementation paths, applicable CI URL/result for the exact SHA, test detail, and runtime/device evidence where required.

A branch, PR, local checkout, PR description, or historical AI report is not proof of current product state.

## 2. Current repository facts

### CURRENT / VERIFIED AT THIS MAIN HEAD

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Android Keystore-based device identity exists and exposes a public-key fingerprint plus public-key DER for device binding; private key material remains in Android Keystore.
- Login/Register are implemented on `main`.
- The Android MVP navigation is implemented on `main`: Login/Register → Device Setup → Dashboard → Device Details → Game Details.
- Dashboard, Device Details and Game Details use authenticated backend APIs rather than the former `CharacterDashboard` placeholder.
- Authenticated device read APIs exist at `GET /v1/devices/me` and `GET /v1/devices/{device_id}`.
- Authenticated entitlement read APIs exist at `GET /v1/entitlements/me` and `GET /v1/entitlements/{entitlement_id}`.
- Device rotate and revoke endpoints exist at `POST /v1/devices/{device_id}/rotate` and `POST /v1/devices/{device_id}/revoke`.
- Device Details now exposes Rotate key and Revoke device actions; revoke clears the local session and returns the user to Login.
- Authorization engine explicitly returns `DENY` when no matching policy exists.
- PostgreSQL schema exists under `server/migrations/001_initial.sql`; the migration numbering issue was resolved by renaming `002_user_auth.sql` to `003_user_auth.sql` without changing its contents.
- The current repository tree contains the Android, FastAPI and web implementation used by the merged MVP navigation.

## 3. CI / evidence status

The current `main` HEAD is `4a0fd8255e4b7beb065e73a254ebb72d3b8b4d11`.

The available GitHub combined-status query for this exact SHA returned no status records. Exact-HEAD workflow PASS/FAIL results and direct run URLs are therefore **not verified in this record**. No older PR run is represented as an exact-HEAD result.

Previously verified PR #37 CI included successful code/build jobs and the known Firebase Test Lab/GCP infrastructure blocker, but those runs were attached to the PR head rather than this resulting merge SHA and are not claimed here as exact-HEAD evidence.

## 4. Keystore / fingerprint status

The Android identity implementation uses `AndroidKeyStore`, EC `secp256r1`, and `SHA256withECDSA`. The client can derive the SHA-256 fingerprint from the encoded public key.

The release fingerprint previously verified in CI was:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

That prior run is not an exact-HEAD verification for `4a0fd8255e4b7beb065e73a254ebb72d3b8b4d11`; exact-head `apksigner verify` evidence is therefore not claimed here.

## 5. OPEN / NOT ACCEPTED ITEMS

### PostgreSQL runtime persistence — OPEN

The current runtime persistence path must still be treated separately from the PostgreSQL schema until exact-main runtime evidence establishes PostgreSQL as the authoritative runtime store.

### Recommendation authorization — OPEN SECURITY GAP

`POST /v1/recommendations` remains an authorization-review item until the endpoint is confirmed to call `policy_engine.authorize` with regression coverage.

### Repository hygiene — OPEN

Historical branches and workflow records still require classification/cleanup. Destructive cleanup remains subject to repository tooling and project rules.

### P1 evidence push trigger — OPEN

`.github/workflows/p1-evidence.yml` currently has `push.branches: [sentinel-1.0.0-rc1-final]` while its pull-request trigger targets `main`. The proposed CI configuration change is intentionally not applied in this state record.

### Deploy workflow anomaly — OPEN INVESTIGATION

The current `.github/workflows/deploy.yml` contains only `release: types: [published]` as its event trigger. The historical push-run anomaly has not been conclusively attributed from the currently available workflow file alone; no claim is made that the present workflow still runs on push.

### Documentation / governance — CURRENT

This file and `README.md` are being updated from the actual current `main` implementation rather than historical pre-merge descriptions.

## 6. Canonical state rules

- `main` is the only canonical product state.
- Architecture documents describe target/contract, not proof of runtime implementation.
- `BRANCH-ONLY` work is not accepted product state.
- A bare `PASS` is prohibited.
- A later main commit that breaks an accepted capability is a `REGRESSION`, not a new feature task.
- Destructive branch/PR cleanup occurs only after classification and preservation of useful history.

## 7. Authority

**Branch-state truth authority:** GPT / Final Integrator.  
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
