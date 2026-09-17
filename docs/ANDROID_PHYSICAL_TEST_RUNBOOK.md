# SENTINEL Android Physical Test Runbook

Status: **ACTIVE — pre-production physical acceptance**

This procedure is for the Human Owner testing the isolated Android physical-test build. It does not publish a release or touch production.

## 1. Use the only correct artifact

Use the artifact named `sentinel-physical-test-apk-<FULL_MAIN_SHA>` from a successful **Physical Test APK** workflow on the exact protected `main` SHA being accepted. Do not use `app-debug.apk`, an artifact from a PR head, or an artifact from an older main commit.

The ZIP must contain exactly:

- `app/build/outputs/apk/physicalTest/app-physicalTest.apk`;
- `physical-test-apk.sha256`;
- `physical-test-manifest.json`.

The manifest must identify:

- repository `spenskoj90-sudo/alpha-0`;
- the same full main SHA as the artifact name;
- application ID `com.alpha0.app.physicaltest`;
- build variant `physicalTest`;
- API environment `staging`;
- API origin `https://sentinel-core-staging.onrender.com`;
- diagnostic mode `FORENSIC_TEST`.

Verify the APK SHA-256 against both `physical-test-apk.sha256` and `physical-test-manifest.json`. On the phone, the red top banner must show `PHYSICAL TEST · STAGING`, the expected version and the first 12 characters of the same source SHA.

## 2. Before installation

Record:

- phone manufacturer/model;
- Android version and security patch level;
- available storage;
- artifact name, full source SHA and APK SHA-256;
- whether the phone is using Wi-Fi or mobile data.

Prerequisites:

- Android 10/API 29 or newer;
- a browser or file manager able to open the downloaded APK;
- permission to install unknown apps for that browser/file manager;
- working Wi-Fi and, if the subscription permits, mobile data;
- an email address and a new staging-only password of at least 12 characters, or an existing staging test account.

Never put the password, tokens, private keys or exported diagnostics in a public issue. The test build does not require a production credential or signing key.

## 3. Install and establish build identity

1. If an older `SENTINEL PHYSICAL TEST` is installed, export any evidence that must be preserved, then uninstall it for the fresh-install pass.
2. Open `app-physicalTest.apk` and allow installation from the selected source when Android asks.
3. Launch **SENTINEL PHYSICAL TEST**.
4. Confirm the permanent red banner says `PHYSICAL TEST · STAGING` and shows the expected version/SHA prefix.
5. Confirm the normal release package, if installed, remains separate. The physical-test package is `com.alpha0.app.physicaltest`.
6. Close and reopen the app once before signing in. A crash loop, blank screen or lost red identity banner is a defect.

## 4. Authentication and first device proof

1. On **SIGN IN**, enter a malformed email and a short password. Expect local validation and no navigation.
2. Enter plausible but invalid existing-account credentials. Expect a bounded authentication error; do not expect access.
3. Select **Create a new account**, enter the staging test email and a password of at least 12 characters, then create the account. For an existing account, sign in instead.
4. Expect **DEVICE SETUP**. Record the displayed fingerprint prefix/algorithm without sharing the full value publicly.
5. If Android offers **Allow background operation**, test both paths during the campaign: first continue without granting it, then return and grant it if supported by the phone.
6. Tap **Привязать и подтвердить устройство** once. Expect bind, one-time challenge signing with Android Keystore, device proof and navigation to **DASHBOARD**.
7. Rapid repeated taps must not create parallel requests; the control is disabled while busy.
8. Background/foreground the app and then force-stop/relaunch it. Expect encrypted session recovery and refresh without another password prompt.

## 5. Dashboard and navigation

1. Confirm the device card loads with an active/secure state.
2. Confirm **GAME ACCESS** shows either assigned entitlements or the explicit empty state. Empty staging entitlements are acceptable; a permanent spinner is not.
3. Open the device card and verify state, algorithm, fingerprint, bound time/last-seen presentation.
4. Return with Android Back. Repeat for every entitlement card that is present.
5. Open **Report a problem**, use Back/Cancel, and confirm navigation returns to the dashboard.
6. Test long system font/display scaling and both supported orientations. Text may wrap/scroll; controls must remain reachable and must not overlap the red build banner.

## 6. Network loss and recovery

Perform these transitions without changing any credential:

1. On Wi-Fi, load the dashboard and device details.
2. Enable airplane mode, then open/reload a server-backed screen. Expect a bounded network error, not a crash or endless spinner.
3. On dashboard load failure, tap **Retry** while still offline. Expect the same recoverable error.
4. Restore Wi-Fi and tap **Retry**. Expect recovery.
5. Switch Wi-Fi → mobile data and repeat a dashboard/device-details request.
6. Switch mobile data → Wi-Fi while the app is backgrounded, then foreground it and retry.
7. Repeat at least three disconnect/reconnect cycles.

The current Android UI has no user-facing gameplay event capture action. Offline queue persistence/idempotency is therefore an automated JVM/Core contract in this build, not a physical UI checkpoint. Do not invent a PASS for a nonexistent phone control.

## 7. Session, key rotation and re-enrollment

1. From the dashboard, tap **Sign out**. Expect Core session revocation followed by the sign-in screen. Authenticated content must no longer be reachable with Back.
2. Sign in again and complete device setup/proof. Expect a usable dashboard.
3. Open **DEVICE DETAILS** and tap **Rotate key** once. Expect a new hardware-backed fingerprint/device binding and a renewed session, then a working dashboard. `KEY_UNCHANGED` is a defect.
4. Force-stop and relaunch after rotation. Expect the rotated identity/session to persist.
5. Leave **Revoke device** until the end because it deliberately invalidates the device and its sessions.
6. Tap **Revoke device**. Expect return to sign-in and denial of the revoked authenticated state.
7. Sign in and bind/prove again if a final recovery pass is required.

## 8. Diagnostics and quality report

1. Reproduce one safe success flow and one offline/network failure.
2. Tap **Export logs** in the red banner. Expect the Android share sheet with a compressed `.jsonl.gz` forensic trace.
3. Save/send it only through the Owner's private evidence channel. Confirm the export action itself does not reveal a password, bearer token, refresh token, private key or raw request body.
4. Open **Report a problem**. Confirm the diagnostic snapshot count/size/mode are shown before entering report text.
5. Submit one staging report without attaching diagnostics.
6. Submit a second clearly labeled staging report with **Attach this diagnostic snapshot** enabled and quality-improvement opt-in left off. Expect a report reference/status.
7. Test the quality-program checkbox separately; it must never become selected automatically when diagnostics are attached.

## 9. Lifecycle, accessibility and stress

- Lock/unlock the screen on login, device setup, dashboard and report form.
- Background/foreground at least ten times, including during an in-flight request.
- Force-stop/relaunch at least three times; reboot once and relaunch.
- Use TalkBack to traverse form fields, password visibility, buttons, cards, errors, progress and status messages.
- Test system font scale at the largest practical setting and verify touch targets remain usable.
- Perform rapid Back/navigation/retry actions and a sustained 20–30 minute normal session.
- Record any thermal, memory, battery, responsiveness, blank-state or focus regression.

## 10. Evidence to return

For every defect send:

- full source SHA and APK SHA-256;
- phone model, Android version/security patch and network type;
- exact numbered step from this runbook;
- expected and actual behavior;
- approximate UTC/local event time;
- safe screenshot or screen recording when useful;
- report reference and/or private exported forensic trace when relevant.

Never send a password, session/access/refresh token, enrollment credential, private key or raw sensitive payload. Physical acceptance is complete only after every applicable checkpoint is observed on the exact-SHA artifact and no unresolved P0/P1 defect remains. CI evidence complements this pass; it does not replace it.
