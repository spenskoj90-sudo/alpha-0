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

For a sideloaded physical-test APK, Google Play Protect may recommend scanning the
application because Google Play has not previously distributed that exact
package/build. This is expected platform behavior, not an application dialog.
Record the result and allow the scan; do not disable or bypass Play Protect.

## 4. Pre-authentication product shell

Complete these checks before entering account credentials:

1. Open the overflow menu in the top app bar. Confirm **Settings**, **Updates**, **Help** and **About** are all reachable, and Android Back returns to sign-in.
2. In **Settings**, select **Русский**. Confirm the visible application interface changes immediately, including sign-in, menu and settings labels.
3. Force-stop and reopen the application. Confirm the selected language persists.
4. Select **English**, then test **Use system language** with the phone configured once in Russian and once in English when practical.
5. Test **System**, **Light** and **Dark** appearance. Each change must apply immediately and persist across force-stop/relaunch. System appearance must follow the current Android system theme.
6. Open **Updates**. Confirm version, channel and source revision are visible. For a sideloaded physical-test build, the screen must explain that Play-distributed automatic updates require the Google Play internal-testing channel; it must not claim that a sideloaded build is Play-managed.
7. Open **Help** and **About**. Confirm the pages are readable at the largest practical font scale and in both light and dark appearance.

## 5. Authentication and first device proof

The free staging Core can be asleep after inactivity. The first authenticated
request may therefore remain in progress for roughly a minute while Render
wakes the service. The physical-test build waits up to 75 seconds for the
authoritative response. Do not tap repeatedly or leave the app while the button
is busy. A registration timeout is an unknown write outcome: wait for staging
and try **Sign in** before attempting to create the account again.

1. On **Sign in / Вход в аккаунт**, enter a malformed email and a short password. Expect local validation and no navigation.
2. Enter plausible but invalid existing-account credentials. Expect a bounded authentication error; do not expect access.
3. Select **Create a new account**, enter the staging test email and a password of at least 12 characters, then create the account. For an existing account, sign in instead.
4. Expect **Device setup / Настройка устройства**. Record the displayed fingerprint prefix/algorithm without sharing the full value publicly.
5. If Android offers **Allow background operation**, test both paths during the campaign: first continue without granting it, then return and grant it if supported by the phone.
6. Confirm the three-step setup page scrolls and the primary action remains reachable at the largest practical font scale and smallest supported display/orientation.
7. Tap **Connect and verify this phone / Подключить и подтвердить телефон** once. Expect bind, one-time challenge signing with Android Keystore, device proof and navigation to **Home / Главная**.
8. Rapid repeated taps must not create parallel requests; the control is disabled while busy.
9. Background/foreground the app and then force-stop/relaunch it. Expect encrypted session recovery and refresh without another password prompt.

## 6. Authenticated navigation

1. Confirm the bottom navigation exposes **Home**, **Games**, **Security** and **Activity**.
2. On **Home**, confirm the device card loads with an active/secure state and the support/report entry point is reachable.
3. On **Games**, confirm assigned entitlements or the explicit empty state. Empty staging entitlements are acceptable; a permanent spinner is not.
4. On **Security**, verify state, algorithm, fingerprint, bound time/last-seen presentation and the rotate/revoke controls.
5. On **Activity**, confirm the application labels local session/device/diagnostic state honestly and does not invent server history.
6. Open every entitlement card that is present, then return with Android Back.
7. Open **Report a problem**, use Back/Cancel, and confirm navigation returns to Home.
8. Test long system font/display scaling and both supported orientations. Text may wrap/scroll; controls must remain reachable and must not overlap the red build banner or bottom navigation.

## 7. Network loss and recovery

Perform these transitions without changing any credential:

1. On Wi-Fi, load the dashboard and device details.
2. Enable airplane mode, then open/reload a server-backed screen. Expect a bounded network error, not a crash or endless spinner.
3. On dashboard load failure, tap **Retry** while still offline. Expect the same recoverable error.
4. Restore Wi-Fi and tap **Retry**. Expect recovery.
5. Switch Wi-Fi → mobile data and repeat a dashboard/device-details request.
6. Switch mobile data → Wi-Fi while the app is backgrounded, then foreground it and retry.
7. Repeat at least three disconnect/reconnect cycles.

The current Android UI has no user-facing gameplay event capture action. Offline queue persistence/idempotency is therefore an automated JVM/Core contract in this build, not a physical UI checkpoint. Do not invent a PASS for a nonexistent phone control.

## 8. Session, key rotation and re-enrollment

1. From the dashboard, tap **Sign out**. Expect Core session revocation followed by the sign-in screen. Authenticated content must no longer be reachable with Back.
2. Sign in again and complete device setup/proof. Expect a usable dashboard.
3. Open **Security** and tap **Rotate device key** once. Expect a new hardware-backed fingerprint/device binding and a renewed session, then a working Home screen. `KEY_UNCHANGED` is a defect.
4. Force-stop and relaunch after rotation. Expect the rotated identity/session to persist.
5. Leave **Revoke device** until the end because it deliberately invalidates the device and its sessions.
6. Tap **Revoke device**. Expect return to sign-in and denial of the revoked authenticated state.
7. Sign in and bind/prove again if a final recovery pass is required.

## 9. Update-channel behavior

1. A physical-test APK installed from a file is a diagnostic instrument. Its Update page must present the sideload/Play-channel limitation accurately.
2. Do not expect a sideloaded package with a different application ID or signing lineage to replace another package in place.
3. After the Owner has created the Google Play application, enrolled the internal-testing account and published a higher-`versionCode` signed build, install from that track and repeat **Updates → Check for updates**.
4. For a Play-installed build, expect the user-confirmed Play update flow without uninstalling the application or losing its local preferences/session. Record the old/new version codes and Play track.
5. Failure to find an unpublished update is not an application PASS or FAIL. The exact Play track, package, signing lineage and version-code ordering are required evidence.

## 10. Diagnostics and quality report

1. Reproduce one safe success flow and one offline/network failure.
2. Tap **Export logs** in the red banner. Expect the Android share sheet with a compressed `.jsonl.gz` forensic trace.
3. Save/send it only through the Owner's private evidence channel. Confirm the export action itself does not reveal a password, bearer token, refresh token, private key or raw request body.
4. Open **Report a problem**. Confirm the diagnostic snapshot count/size/mode are shown before entering report text.
5. Submit one staging report without attaching diagnostics.
6. Submit a second clearly labeled staging report with **Attach this diagnostic snapshot** enabled and quality-improvement opt-in left off. Expect a report reference/status.
7. Test the quality-program checkbox separately; it must never become selected automatically when diagnostics are attached.

## 11. Lifecycle, accessibility and stress

- Lock/unlock the screen on login, settings, device setup, every primary destination and the report form.
- Background/foreground at least ten times, including during an in-flight request.
- Force-stop/relaunch at least three times; reboot once and relaunch.
- Use TalkBack to traverse form fields, password visibility, buttons, cards, errors, progress and status messages.
- Test system font scale at the largest practical setting and verify touch targets remain usable.
- Perform rapid Back/navigation/retry actions and a sustained 20–30 minute normal session.
- Record any thermal, memory, battery, responsiveness, blank-state or focus regression.

## 12. Evidence to return

For every defect send:

- full source SHA and APK SHA-256;
- phone model, Android version/security patch and network type;
- exact numbered step from this runbook;
- expected and actual behavior;
- approximate UTC/local event time;
- safe screenshot or screen recording when useful;
- report reference and/or private exported forensic trace when relevant.

Never send a password, session/access/refresh token, enrollment credential, private key or raw sensitive payload. Physical acceptance is complete only after every applicable checkpoint is observed on the exact-SHA artifact and no unresolved P0/P1 defect remains. CI evidence complements this pass; it does not replace it.
