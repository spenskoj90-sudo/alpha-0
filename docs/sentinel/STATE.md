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

The modernization and Core work is currently isolated in PR #1 / `agent/modernize-alpha0` and is not part of `main` until accepted.

## Implemented in source

### Android foundation

- Android application shell
- Android Keystore-backed P-256 device identity
- SHA-256 public-key fingerprint
- ECDSA `SHA256withECDSA` signing and local verification
- Deterministic hexadecimal encoding
- JVM fingerprint/hex tests
- Android CI configuration

### Sentinel Core foundation

- Kotlin/JVM `core` module
- deterministic authorization domain model
- explicit role membership requirement
- permission check independent from role
- versioned scope ruleset
- entitlement status/time-window evaluation
- policy evaluation
- context validation
- explicit `ALLOW` / typed `DENY` decisions
- regression tests for positive and deny paths

The Core authorization engine is a domain foundation only. It is not yet exposed through a server/API and must not be treated as completed server-side authorization.

## Not yet implemented

- Device registration
- Server-side device binding and verification
- Session management
- Device revocation
- PostgreSQL persistence
- Server/API adapter around Core authorization
- Audit persistence
- Network resilience
- Recovery flows

## Evidence status

- Source inspection: verified
- Build execution on current modernization/Core head: pending / CI status must be checked
- Runtime Android identity verification: not yet performed
- Server security verification: not yet implemented
- Performance benchmark: not performed

## Next vertical slice

Device Registration → Server-side Challenge Verification → Persistence → Audit → protected operation through the Core authorization engine.

Minimum security outcomes:

- unknown device → DENY
- unbound device → DENY
- invalid signature → DENY
- modified challenge → DENY
- malformed request → DENY
- valid bound device → authenticated context
- missing role/permission/scope/entitlement/policy/context → DENY

## Continuity rule

Missing context is `UNKNOWN`, never `PASS`. GitHub state takes precedence over chat summaries.
