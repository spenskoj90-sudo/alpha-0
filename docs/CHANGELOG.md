# Changelog

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
