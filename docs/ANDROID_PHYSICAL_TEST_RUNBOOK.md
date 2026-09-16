# SENTINEL Android Physical Test Runbook

Status: pre-production physical acceptance procedure.

## Test artifact

Use only the `Physical Test APK` artifact produced from the exact protected `main` SHA being accepted. The artifact name is `sentinel-physical-test-apk-<SHA>` and contains `app-physicalTest.apk` plus `physical-test-apk.sha256`.

The physical-test variant is intentionally isolated from production (`com.alpha0.app.physicaltest`), debuggable, non-minified, and runs diagnostics in `FORENSIC_TEST` mode. CI binds this variant to the HTTPS staging Core at `https://sentinel-core-staging.onrender.com`. Do not use a generic debug APK for physical acceptance.

## Before installation

1. Record phone model, Android version, security patch level, available storage, network type, and the exact Git SHA from the artifact name.
2. Verify the APK SHA-256 against `physical-test-apk.sha256` before installation.
3. Confirm the staging Core is reachable over HTTPS from the phone network.
4. Preserve screenshots/screen recordings only when they do not expose enrollment credentials, bearer tokens, device secrets, or other sensitive values.

## Acceptance pass

Perform the following on the physical-test build and record PASS/FAIL plus evidence for each section.

### Installation and lifecycle

- Install from a clean state and launch.
- Background/foreground repeatedly.
- Rotate the device where the OS/app permits it.
- Force-stop and relaunch.
- Reboot the phone and relaunch.
- Verify no crash loop, blank screen, unrecoverable loading state, or lost authenticated state beyond documented security behavior.

### Enrollment and authentication

- Complete the supported staging enrollment/login flow.
- Verify device identity is created and subsequent authenticated requests work.
- Exercise logout and login again.
- Verify invalid/expired credentials fail closed and the UI gives a recoverable path.
- Never paste credentials or tokens into an issue or chat transcript.

### Connectivity and recovery

- Exercise Wi-Fi, mobile data, and a network-loss period when available.
- While offline, perform operations that are designed to queue/retry.
- Restore connectivity and verify recovery without duplicate visible actions or permanent spinner states.
- Switch networks while the app is foregrounded and while backgrounded.

### Core user flows

- Traverse every reachable primary screen and navigation destination.
- Exercise empty, loading, success, validation-error, server-error, and retry states that can be reached safely.
- Verify back navigation, repeated taps, refresh/retry actions, and state restoration.
- Check text truncation, keyboard overlap, scrolling, touch targets, dark/light system behavior where supported, and large-font/display scaling.

### Security and privacy behavior

- Confirm sensitive values are not visibly exposed in normal UI, diagnostics previews, notifications, or exported evidence.
- Confirm security-sensitive failures fail closed rather than silently succeeding.
- Confirm logout removes access to authenticated content.
- Confirm screenshots/recents behavior is consistent with the implemented security policy on sensitive surfaces.

### Diagnostics / forensic-test evidence

- Exercise the in-app diagnostics surfaces available in `FORENSIC_TEST` mode.
- Generate/export the supported diagnostic bundle after representative success and failure scenarios.
- Confirm the bundle is bounded and redacted; do not upload it publicly if it contains user-specific data.
- Record the exact source SHA shown by the build/runtime when available.

### Stress and interruption

- Perform rapid navigation and repeated refresh/retry operations.
- Background the app during an in-flight request, then resume.
- Force-stop during a recoverable operation, then relaunch.
- Run a sustained session long enough to observe thermal, memory, battery, and responsiveness regressions.

## Evidence to return

For each defect provide: exact artifact SHA, phone model, Android version, network type, reproduction steps, expected result, actual result, screenshot/video when safe, and the exported redacted diagnostic bundle when relevant.

A physical acceptance PASS means all applicable sections above were exercised on the exact-SHA physical-test artifact without an unresolved P0/P1 defect. Physical evidence complements CI; it does not replace required repository checks.
