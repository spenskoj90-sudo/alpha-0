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
- Replaced the Linux hosted emulator path with `macos-15-intel` for the dedicated instrumentation job.
- The previous Linux failure was caused by unavailable `/dev/kvm`, persistent ADB `device offline`, and cleanup exit code 224; no application assertion failure was observed.
- macOS Intel was selected over Firebase Test Lab because it requires only a runner-label change, keeps the existing Gradle/instrumentation test contract, avoids adding cloud credentials/project/IAM/billing dependencies, and uses the Android Emulator's native macOS Hypervisor.framework path. Firebase Test Lab remains a valid alternative if cloud-device coverage is preferred. Self-hosted KVM is intentionally not introduced without a human infrastructure decision.

### Reproducible deployment
- Added a CI gate that performs an independent no-cache Docker rebuild and compares image identity plus root filesystem layer digests.
- First exact-head reproducibility run failed because the locally built `sentinel-core` wheel changed between builds despite the same base image and dependency versions. The build backend was range-pinned and pip was floating.
- Pinned the Docker base image digest, pip `26.2.1`, setuptools `80.9.0`, disabled build isolation, and set `SOURCE_DATE_EPOCH=0`, `PYTHONHASHSEED=0`, and `TZ=UTC`.
- Second exact-head reproducibility run showed the wheel itself was now byte-identical (`c60960a29f...` in both builds), but the first differing final-image layer was the runtime `addgroup/adduser` layer. The layer changed because creating system users mutates `/etc/passwd`/`/etc/group` with build-time metadata. Removed that runtime mutation and switched to the fixed numeric non-root identity `USER 10001:10001`. A new exact-head comparison is required for final proof.

### Full Validation evidence
- Exact-head validation is run from branch `p1-close-2026-08-13`; final evidence must reference the resulting exact HEAD only.
- The synthetic PR merge SHA remains distinct from the release-candidate branch HEAD and is never relabeled as exact-head evidence.

### Evidence policy
- Release status is based only on CI evidence from the selected exact release commit.
- Architecture documents, mockups and screenshots are not runtime evidence.
- Gate A, production-level backup/restore, production load characterization and live Stripe remain explicit external gates.

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
