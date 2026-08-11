# SENTINEL — Alpha-0 Development State

## Current stage

Alpha-0 full runnable security vertical slice

## Target

Minimal Alpha Release Candidate

## Source of truth

- Source code: GitHub repository `spenskoj90-sudo/alpha-0`
- Accepted architecture: Architecture v3
- Implementation constraints: Implementation Contract v1
- Verification: Test Matrix v1
- Decisions: Decision Log

## Repository visibility

The GitHub repository is now **public**. Public-release hardening is therefore part of the active security boundary.

## Current authoritative branch

`main` remains the accepted baseline. The completed hardening/full-validation work is isolated in PR #1 / `agent/modernize-alpha0` until runtime evidence and review are complete.

## Implemented in source

### Android

- Android Keystore-backed P-256 device identity
- SHA-256 public-key fingerprint
- ECDSA `SHA256withECDSA`
- runtime crypto self-test and private-key non-exportability check
- cleartext traffic disabled
- backup/device-transfer extraction disabled
- JVM tests
- Android instrumentation smoke test and emulator CI
- debug CI does not require production signing secrets

### Authorization

- centralized Default Deny engine
- Role + Permission + Scope + Entitlement + Policy + Context checks
- bounded inputs
- fail-closed policy exceptions
- typed ALLOW/DENY decisions
- server-side authorization middleware
- protected HTTP endpoint enforcement
- protected authorization ALLOW/DENY decisions audited when a durable audit sink is configured
- audit persistence failure fails closed

### Device lifecycle

- `PENDING → ACTIVE → REVOKED`
- registration never grants authorization
- fingerprint is cryptographically derived from the submitted public key
- active binding required before proof acceptance
- one-time recovery codes
- atomic recovery/key rotation

### Authentication challenge

- server-issued challenge nonce
- 32–64 byte nonce bounds
- exact P-256 enforcement
- expiry before crypto and re-check before consume
- replay protection
- constant-time fingerprint comparison
- trusted challenge state only
- transactional challenge-consumption + mandatory ALLOW audit persistence

### Sessions

- opaque 256-bit bearer credentials
- SHA-256 token digests only at rest
- bounded 30-day lifetime
- expiry and revocation
- atomic session rotation
- old credential invalidated during rotation
- PostgreSQL persistence

### PostgreSQL

- device/challenge/session/audit/recovery persistence
- integrity constraints and indexes
- challenge expected fingerprint is mandatory
- audit subject/action bounds
- device timestamp ordering constraint
- PostgreSQL TLS + channel binding required by runtime configuration
- bounded connection/socket timeouts
- canonical schema and migrations

### Server

- standalone JVM server
- localhost-by-default
- bounded request bodies and form fields
- strict form content type
- duplicate request parameters rejected
- bounded in-process per-client rate limiting
- security response headers
- graceful shutdown hook
- health endpoint
- device registration/activation
- recovery/key rotation
- server-issued challenges
- proof verification
- session issue/rotate/revoke
- protected authorization endpoint
- no raw bearer-token logging

### Public-repository / supply-chain hardening

- Dependabot for Gradle and GitHub Actions
- Dependency Review gate for pull requests
- CodeQL
- minimal workflow `GITHUB_TOKEN` permissions
- public PR CI does not require production signing secrets
- Android checkout disables persisted Git credentials
- release signing remains isolated to tag/manual release workflow
- `.gitignore` excludes signing material and local secrets
- `SECURITY.md` documents vulnerability handling

### Validation

- Android build/test/lint CI
- CodeQL
- Dependabot
- dependency review
- full JVM/server validation workflow
- PostgreSQL TLS-backed server E2E workflow
- Android emulator instrumentation workflow
- bounded security stress tests
- failure-injection/fail-closed regression coverage
- signed production release workflow
- APK signature and SHA-256 verification

## Known regression fixed in current cycle

`AuthorizationMiddlewareTest` previously passed the deterministic clock lambda as the trailing SAM argument, where Kotlin interpreted it as `AuditSink`. The test therefore failed compilation with `Instant` versus `Boolean`. The test now uses explicit named arguments (`now = ...`, `auditSink = ...`) so the intended dependency injection is unambiguous.

## Evidence still required

Source implementation is substantially complete, but runtime acceptance still requires the current GitHub Actions cycle to finish successfully and, separately, production environment evidence for:

- real PostgreSQL deployment configuration;
- Android device/emulator instrumentation;
- server E2E;
- performance/chaos gates;
- production release signing with repository secrets;
- API gateway/TLS termination configuration.

These are execution/deployment gates, not missing domain implementations.

## Security acceptance matrix

- unknown/unbound device → DENY
- invalid signature → DENY
- modified challenge → DENY
- unknown/expired/replayed challenge → DENY
- device/key mismatch → DENY
- non-P256 key → DENY
- challenge-store failure → DENY
- malformed/oversized authorization input → DENY
- missing role/permission → DENY
- scope mismatch → DENY
- invalid/expired entitlement → DENY
- policy denial/exception → DENY
- invalid context → DENY
- audit persistence failure → DENY
- expired/revoked session → DENY
- stale session after rotation → DENY
- revoked device → DENY
- invalid/expired recovery code → DENY
- oversized/malformed HTTP body → DENY
- duplicate form parameter → DENY
- unsupported form content type → DENY
- excessive request rate → DENY
- valid bound device + valid authorization context + successful audit → ALLOW

## Acceptance rule

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

No source-only claim is promoted to runtime PASS.

## Continuity rule

Missing context is `UNKNOWN`, never `PASS`. GitHub state takes precedence over chat summaries.
