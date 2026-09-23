# Android physical evidence — 2026-09-23

**Evidence label:** INTEGRATION-TESTED / PHYSICAL-TEST-OBSERVED  
**Diagnostic source:** Google Drive bundle `1N_goLojUz_BUxFW_HVDNfqVxQgiCQt-7`  
**Bound source SHA:** `b218cab8130afbe3e413a9e7f2beb53e034a8daa`  
**Build:** `1.0.0-rc2-physical-test` / versionCode `100000199`  
**Device:** Infinix X6731B / Android API 34

## Diagnostic summary

216 events were parsed: 205 SUCCESS, 5 OBSERVED, 3 SKIPPED, 2 FAILURE and 1 MFA_REQUIRED. No recorded crash or ANR was present in the bundle.

Verified flows include password login, MFA challenge/completion, Android Keystore identity, StrongBox-unavailable fallback to TEE, device bind/proof, entitlements, session refresh, RU/EN/System locale, Light/Dark/System appearance, rotation/recreation, task removal, clean restart and explicit diagnostics export.

Visual acceptance for the prior UI is **FAILED** and is not carried forward as v3 acceptance.

## StrictMode classification

Two VM violations were recorded as `LeakedClosableViolation`. Both stacks are confined to Android framework finalization:

`StrictMode.AndroidCloseGuardReporter → dalvik.system.CloseGuard → android.view.SurfaceControl.finalize → FinalizerDaemon`

The recorded callsite is `InsetsSourceControl`; no `com.alpha0.app` or Compose application frame exists in either stack.

**Classification:** PLATFORM/FRAMEWORK-OBSERVED, not proven app-owned.

The warning is not suppressed. If a future exact-SHA physical bundle includes an application-owned allocation/close stack, classification must be reopened and the application leak fixed.

## Staging latency evidence

Observed cold/warm timings from the bundle:

| Operation | Observed duration |
| --- | ---: |
| provider catalog, first | ~34.6 s |
| login → MFA required | ~16.5 s |
| device bind | ~17.5 s |
| MFA completion | ~7.5 s |
| first refresh after recreation | ~7.4 s |
| later cold refresh sample | ~8.6 s |
| warm refresh | ~0.9 s |
| device proof | ~0.28 s |
| warm dashboard API requests | ~0.18–0.43 s |

The gap between cold and warm paths is consistent with a staging wake/cold-start component, but this physical bundle alone does **not** prove the exact split among Render scheduling, DNS/TLS, server startup, database wake or network conditions. Exact decomposition requires correlated Render request/runtime evidence.

The v3 Android request diagnostics now preserve request correlation and total client duration on success, HTTP failure, network failure and unexpected failure so the next physical bundle can be matched against server-side request timing without fake progress.

## Next physical acceptance

The next physical run must bind diagnostics to the new exact PR/main SHA and re-check:

- launcher/splash optical identity;
- bottom navigation and 48dp reach targets;
- compact PHYSICAL TEST strip;
- RU/EN/System and Light/Dark/System;
- rotation/background/force-stop/network loss/recovery;
- TalkBack and font scaling;
- cold-path correlated timing;
- whether the same framework-only StrictMode signature recurs.

Until that run, v3 target-device visual acceptance is **ENVIRONMENT-UNVERIFIED**.
