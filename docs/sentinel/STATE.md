# SENTINEL — Alpha-0 Development State

## Current stage

Alpha-0

## Target

Minimal Alpha Release Candidate

## Source of truth

- Source code: GitHub repository `spenskoj90-sudo/alpha-0`
- Accepted architecture: Architecture v3
- Implementation constraints: Implementation Contract v1
- Verification: Test Matrix v1
- Decisions: Decision Log

## Current authoritative branch

`main` — `b8ab17fdaf3193094dff8234596dba866af73262`

The modernization work is currently isolated in PR #1 / `agent/modernize-alpha0` and is not part of `main` until accepted.

## Implemented in source

- Android application shell
- Android Keystore-backed P-256 device identity
- SHA-256 public-key fingerprint
- ECDSA `SHA256withECDSA` signing and local verification
- Deterministic hexadecimal encoding
- JVM fingerprint/hex tests
- Android CI configuration

## Not yet implemented

- Device registration
- Server-side device binding and verification
- Session management
- Device revocation
- Sentinel Core
- PostgreSQL persistence
- Server-side authorization
- RBAC + Scope
- Entitlement
- Policy
- Context evaluation
- Audit persistence

## Evidence status

- Source inspection: verified
- Build execution on current modernization head: pending / CI in progress
- Runtime device verification: not yet performed
- Server security verification: not yet implemented
- Performance benchmark: not performed

## Next vertical slice

Device Registration → Server-side Challenge Verification → Persistence → Audit.

Minimum security outcomes:

- unknown device → DENY
- unbound device → DENY
- invalid signature → DENY
- modified challenge → DENY
- malformed request → DENY
- valid bound device → ALLOW

## Continuity rule

Missing context is `UNKNOWN`, never `PASS`. GitHub state takes precedence over chat summaries.
