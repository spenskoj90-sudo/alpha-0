# Android physical-test findings — 2026-09-23

Evidence bundle: Google Drive ID `1N_goLojUz_BUxFW_HVDNfqVxQgiCQt-7`, source SHA `b218cab8130afbe3e413a9e7f2beb53e034a8daa`, build `1.0.0-rc2-physical-test`, versionCode `100000199`, device `Infinix X6731B`, Android API 34.

## Result summary

216 events: 205 SUCCESS, 5 OBSERVED, 3 SKIPPED, 2 FAILURE, 1 MFA_REQUIRED. No recorded crash or ANR.

## StrictMode classification

The two FAILURE records are `VM_VIOLATION / LeakedClosableViolation`. Both stacks terminate inside Android framework finalization: `StrictMode.AndroidCloseGuardReporter`, `dalvik.system.CloseGuard`, `android.view.SurfaceControl.finalize`, FinalizerDaemon. Neither stack contains a SENTINEL package frame or a Compose frame.

AOSP `InsetsSourceControl` owns a framework-created `SurfaceControl` named `InsetsSourceControl`; CloseGuard reports leaked-closable violations during finalization. On the available physical evidence, these two observations are classified **FRAMEWORK/PLATFORM-OBSERVED**, not app-owned. Vendor timing remains possible because this evidence came from one API-34 Infinix device.

The events remain visible. StrictMode detection is not disabled or suppressed. Reclassification to app-owned is required if a future stack contains a SENTINEL frame or a reproducible app-owned resource path.

## Latency evidence

Measured cold-path durations in the physical bundle:

- provider catalog: 34,567 ms cold; subsequent samples 114–132 ms;
- login to MFA-required response: 16,513 ms;
- MFA completion: 7,463 ms;
- device bind: 17,474 ms;
- session refresh after lifecycle transition: 7,355–8,605 ms on cold/recovery samples;
- warm session refresh: 887–957 ms;
- warm device/entitlement API calls: approximately 180–428 ms.

The warm API timings show that Compose rendering/serialization is not the dominant contributor to the 7–35 second cold samples. The pattern is consistent with staging service wake/cold-start plus network/TLS and server work; exact server/network split requires correlated staging request logs. Android request diagnostics now preserve the request correlation ID on REQUEST_START as well as REQUEST_COMPLETE, include total duration on failure paths, and label the measured phase `client_total`.

No fake progress timing is introduced. UI state remains bound to authoritative network completion.

## Evidence labels

- physical flows on baseline bundle: **INTEGRATION-TESTED / PHYSICAL-EVIDENCE**;
- StrictMode classification: **OBSERVED / FRAMEWORK-PLATFORM**, pending repetition on additional devices;
- new request correlation instrumentation: **IMPLEMENTED**, pending next physical bundle;
- server/network cold-start split: **ENVIRONMENT-UNVERIFIED** until staging log correlation is available.
