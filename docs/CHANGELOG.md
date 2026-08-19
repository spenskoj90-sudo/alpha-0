# Changelog

## 1.0.0-RC1 — 2026-08-13

### P1 pass continuation
- Added deterministic entitlement decision engine with fail-closed handling for missing, suspended, future and expired entitlements.
- Added provider-neutral billing runtime state transitions; live Stripe credentials and production provider calls remain intentionally out of scope.
- Added outbox and worker state machines with duplicate protection, attempt counting, retry and completion semantics.
- Added explicit PostgreSQL RLS policies with fail-closed service-policy opt-in.
- Added P1 evidence workflow producing exact-SHA Python, npm and Gradle dependency artifacts plus performance output.
- Added P1 runtime regression tests.
- Added server-side device rotate/revoke lifecycle: rotation atomically invalidates the old device/session path, creates a new device key binding and challenge, and device revoke invalidates all sessions for that device.
- Added an API integration test covering rotate → old-session denial → new-key proof → new-session authorization → revoke → denial for both new and old credentials.

### Android instrumentation infrastructure
- Replaced the Linux hosted emulator path with Firebase Test Lab instrumentation using the existing Android debug and test APK artifacts.
- The previous Linux failure was caused by unavailable `/dev/kvm`, persistent ADB `device offline`, and cleanup exit code 224; no application assertion failure was observed.
- Firebase Test Lab was selected over hosted macOS virtualization because it removes the established HVF/KVM virtualization dependency from the CI runner and executes instrumentation on managed Android infrastructure. Self-hosted KVM remains an alternative requiring a separate human infrastructure decision.

### Gate A / Android release signing
- Gate A is now closed by the owner through repository GitHub Actions Secrets: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, and `ANDROID_KEY_PASSWORD`.
- Release signing decodes the keystore only into `$RUNNER_TEMP`, verifies the release artifact certificate SHA-256 fingerprint, and invokes `assembleRelease` with secrets supplied only through the workflow environment.
- The previous PKCS12 keystore was retired because it could not support the required different store/key passwords. The replacement keystore uses alias `sentinel_release` with identical store and key passwords.
- The active release certificate fingerprint is now `43:5A:F3:E5:7E:0B:0D:1F:AE:38:6B:B4:52:C3:45:F9:3A:4F:FD:83:56:AE:E9:D8:63:F5:EF:69:DD:26:BD:C1`. The superseded fingerprint is no longer valid.
- The private keystore, passwords and private key are not stored in the repository or exposed to the agent.

### Reproducible deployment
- Added a CI gate that performs an independent no-cache Docker rebuild and compares image identity plus root filesystem layer digests.
- First exact-head reproducibility run failed because the locally built `sentinel-core` wheel changed between builds despite the same base image and dependency versions. The build backend was range-pinned and pip was floating.
- Pinned the Docker base image digest, pip `26.2.1`, setuptools `80.9.0`, disabled build isolation, and set `SOURCE_DATE_EPOCH=0`, `PYTHONHASHSEED=0`, and `TZ=UTC`.
- Second exact-head reproducibility run showed the wheel itself was now byte-identical (`c60960a29f...` in both builds), but the first differing final-image layer was the runtime `addgroup/adduser` layer. The layer changed because creating system users mutates `/etc/passwd`/`/etc/group` with build-time metadata. Removed that runtime mutation and switched to the fixed numeric non-root identity `USER 10001:10001`.
- Final exact-head reproducibility evidence is required for the current release commit; no reproducibility status is inferred from a successful Docker build alone.

### Full Validation evidence
- Exact-head validation is run from branch `sentinel-ftl-2026-08-13`; final evidence must reference the resulting exact HEAD only.
- The synthetic PR merge SHA remains distinct from the release-candidate branch HEAD and is never relabeled as exact-head evidence.

### Evidence policy
- Release status is based only on CI evidence from the selected exact release commit.
- Architecture documents, mockups and screenshots are not runtime evidence.
- Gate A is closed. Production-level backup/restore, production load characterization and live Stripe remain explicit external gates.

## 1.0.0-RC1 — 2026-08-12

### Added
- Server-authoritative default-deny authorization.
- User-bound Android device enrollment and P-256 proof.
- Opaque access sessions with refresh rotation/replay detection.
- PostgreSQL production persistence and checksum-verified migrations.
- Device-bound idempotent event ingestion.
- Audit and security-failure persistence.
- Diablo catalog, entitlement gate, admin entitlement control and WoW support.
- Android secure-session storage hardening.
- Web control-plane build/lint pipeline.
- Docker and GitHub Actions release automation.
- CodeQL, Trivy, dependency and coverage gates.

### Security
- Added CSP, frame, content-type, referrer, permissions and production HSTS headers.
- Removed debug-build dependence on release signing secrets.
- Added secret-pattern CI checks.

### Release notes
- RC1 is accepted only when the exact commit has green CI evidence.
- Production requires externally managed secrets and TLS termination.