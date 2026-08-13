# Changelog

## 1.0.0-RC1 — 2026-08-13

### P1 pass continuation
- Added deterministic entitlement decision engine with fail-closed handling for missing, suspended, future and expired entitlements.
- Added provider-neutral billing runtime state transitions; live Stripe credentials and production provider calls remain intentionally out of scope.
- Added outbox and worker state machines with duplicate protection, attempt counting, retry and completion semantics.
- Added explicit PostgreSQL RLS policies with fail-closed service-policy opt-in.
- Added P1 evidence workflow producing exact-SHA Python, npm and Gradle dependency artifacts plus performance output.
- Added P1 runtime regression tests.

### Full Validation evidence
- Android build/tests, PostgreSQL integration/recovery, Web build, Container build, Deployment smoke/health and repository verification are green for Build & Test run `31675634466`.
- Android instrumentation remains an infrastructure-bound gate while the hosted emulator/ADB rerun is unresolved; no instrumentation assertion failure has been observed in the available logs.
- The synthetic PR merge SHA `e707dc43e4b34060217c2319dccb5b3ef2022adb` is kept distinct from release-candidate HEAD `8888c17c64af6a981d054dce7f74ca3bb6b4dada`.

### Evidence policy
- Release status is based only on CI evidence from the selected exact release commit.
- Architecture documents, mockups and screenshots are not runtime evidence.
- Production-level backup/restore, reproducible deployment comparison, live Stripe integration and external keystore/secrets remain explicit external gates.

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
