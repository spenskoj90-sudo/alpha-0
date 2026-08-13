# Changelog

## 1.0.0-RC1 — 2026-08-13

### P0 audit closure work
- Enforced an explicit authorization policy for `POST /v1/recommendations` using the same server-side authorization layer as other sensitive endpoints.
- Added the P0 negative security regression suite covering nonce invalidity/reuse/expiry, signature and payload tampering, stale timestamps, revoked devices, rotated keys, expired/revoked sessions, missing scope, wrong role, explicit deny, direct unauthorized recommendation calls, cross-device events, duplicate events and sequence replay.
- Kept event request hashing independent of transport `request_id` and preserved idempotency-key conflict detection.
- Kept production runtime fail-closed on missing `DATABASE_URL`; production uses `PostgresStore`, while `MemoryStore` remains a deterministic test/development double.

### Evidence policy
- Release status is based only on CI evidence from the selected exact release commit.
- Architecture documents, mockups and screenshots are not runtime evidence.
- Remaining P1 capabilities are not marked implemented until their runtime evidence exists.

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
