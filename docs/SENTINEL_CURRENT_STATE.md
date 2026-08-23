# SENTINEL — Canonical Current State

**State record:** 2026-08-23  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD:** `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79`

> This document is repository-grounded. It separates current `main` implementation from architecture, branch-only work, historical evidence, and unverified AI claims.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. `VERIFIED` requires the seven-part evidence bundle: exact SHA, main-line reachability, relevant implementation paths, applicable CI URL/result for the exact SHA, test detail, and runtime/device evidence where required.

A branch, PR, local checkout, PR description, or historical AI report is not proof of current product state.

## 2. Current repository facts

### CURRENT / VERIFIED ON MAIN

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Android Keystore-based device identity exposes public-key fingerprint and DER for binding; private key material remains in Android Keystore.
- Login/Register are implemented in the login screen's register mode.
- Complete Android MVP navigation is implemented: Login/Register → Device Setup → Dashboard → Device Details → Game Details.
- Dashboard, Device Details and Game Details use authenticated backend APIs.
- Authenticated device and entitlement read APIs exist.
- Device rotate/revoke endpoints exist at `POST /v1/devices/{device_id}/rotate` and `POST /v1/devices/{device_id}/revoke`; duplicate routes were removed from `wow_api.py`.
- `/v1/devices/bind` binds the authenticated session to the device.
- Session/device lifecycle security regression coverage exists.
- Final Sentinel design system is merged: centralized final palette, Outfit/Inter/JetBrains Mono typography, 4dp cards, 2dp ultraviolet left accent, cyan/danger status badges, rounded primary/destructive controls, and one-shot 1000ms scan-line on Dashboard Device and Device Details State/Security cards.
- `.github/workflows/p1-evidence.yml` uses `push.branches: [main]` and `pull_request.branches: [main]`.
- `.github/workflows/deploy.yml` currently declares only `release.published`.

## 3. CI / evidence status

PR #46 exact-head commit: `43f94338df4da82917e615b2e1c9eb79014e9246`.

- Security #170 / run `32626297508` — PASS.
- P1 Evidence #80 / run `32626297477` — PASS.
- ALPHA-0 Android CI #1022 / run `32626297516` — PASS.
- Build & Test #250 / run `32626297494` — all product/code/build jobs PASS; Firebase Test Lab failed at Google Cloud authentication and instrumentation was skipped. This is the known FTL/GCP infrastructure exception.

PR #46 was merged into main as `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79`. The PR tree was the accepted tree; no pre-merge PR run is represented as a distinct post-merge run for the merge SHA.

## 4. Keystore / fingerprint status

The Android identity implementation uses `AndroidKeyStore`, EC `secp256r1`, and `SHA256withECDSA`. The client derives the SHA-256 fingerprint from the encoded public key.

The release fingerprint previously verified in CI was:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

That fingerprint remains historical evidence rather than a new exact-main `apksigner verify` result for `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79`.

## 5. P0 / runtime findings

### P0 TCP bug — CLOSED AS ENVIRONMENTAL

The local plaintext-server BrokenPipeError was traced to aggressive battery/background-network restrictions on the user's device, not to an HTTP/TLS/h2c defect. The Android client uses `HttpURLConnection`. After battery optimization was disabled for the application, the first request completed immediately and the authenticated device flow continued. PR #34 supplied the diagnostic exception reporting used during this investigation.

## 6. OPEN / NOT ACCEPTED ITEMS

### PostgreSQL runtime persistence — OPEN

Schema/migration evidence is present, but current-main runtime persistence must still be demonstrated before PostgreSQL is declared the authoritative runtime system of record.

### Recommendation authorization — OPEN SECURITY GAP

`POST /v1/recommendations` remains under review until confirmed to call `policy_engine.authorize` with regression coverage.

### Repository hygiene — OPEN / PARTIAL

Historical branches/PRs, ghost workflow records and duplicate state documents still require classification and controlled cleanup.

### Deploy workflow anomaly — OPEN INVESTIGATION

Current `deploy.yml` has no push trigger. Historical push-associated Deploy runs remain unattributed to a specific workflow revision.

## 7. Canonical state rules

- `main` is the only canonical product state.
- Architecture documents describe target/contract, not proof of runtime implementation.
- `BRANCH-ONLY` work is not accepted product state.
- A bare `PASS` is prohibited.
- A later main commit that breaks an accepted capability is a `REGRESSION`, not a new feature task.
- Destructive branch/PR cleanup occurs only after classification and preservation of useful history.

## 8. Authority

**Branch-state truth authority:** GPT / Final Integrator.  
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.