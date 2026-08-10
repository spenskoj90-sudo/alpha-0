# SENTINEL — Alpha-0 Development State

## Current stage

Alpha-0 hardening / reliability vertical slice

## Target

Minimal Alpha Release Candidate

## Source of truth

- Source code: GitHub repository `spenskoj90-sudo/alpha-0`
- Accepted architecture: Architecture v3
- Implementation constraints: Implementation Contract v1
- Verification: Test Matrix v1
- Decisions: Decision Log

## Current authoritative branch

`main` remains the accepted baseline. The modernization and security work is isolated in PR #1 / `agent/modernize-alpha0` until CI and review evidence are complete.

## Implemented in source

### Android foundation

- Android application shell
- Android Keystore-backed P-256 device identity
- SHA-256 public-key fingerprint
- ECDSA `SHA256withECDSA` signing and local verification
- deterministic hexadecimal encoding
- runtime cryptographic self-test
- explicit non-exportability self-test for the Keystore private key
- cleartext traffic disabled
- backup/device-transfer extraction disabled
- JVM fingerprint/hex tests
- Android build, lint and artifact CI

### Sentinel Core authorization

- centralized Default Deny authorization engine
- explicit required-role membership
- permission check independent from role
- versioned scope ruleset with structural validation
- entitlement status/time-window evaluation
- policy evaluation with fail-closed exceptions
- context validation
- bounded roles, permissions, scope rules and context attributes
- explicit `ALLOW` / typed `DENY` decisions

### Device enrollment / binding

- explicit `PENDING` / `ACTIVE` / `REVOKED` device state model
- registration does not grant authorization
- activation is a separate state transition
- revoked devices cannot be reactivated through the normal activation path
- registration requires an actual P-256 public key
- supplied fingerprint must match the submitted public key
- store failures fail closed
- active binding is checked before cryptographic proof acceptance
- PostgreSQL device registry implementation

### Device challenge security

- server-side P-256 challenge/signature verification boundary
- server-side challenge issuance
- client submits only challenge ID, public key and signature for proof
- trusted server-issued nonce, expiry and expected fingerprint
- 32–64 byte challenge nonce bound
- bounded challenge ID, public-key and signature inputs
- exact `secp256r1` parameter enforcement, not only field-size checks
- challenge expiry before expensive cryptography
- expiry re-check immediately before atomic consumption
- atomic challenge-consume contract for replay prevention
- constant-time fingerprint comparison
- challenge-store failures fail closed
- mandatory audit acknowledgement for successful verification
- audit failure denies
- active binding required before proof acceptance
- regression coverage for positive, negative, replay, substitution, expiry, malformed, oversized, non-P256, revoked-device and storage-failure paths

### PostgreSQL persistence

- PostgreSQL JDBC 42.7.13
- `JdbcChallengeStore`
- `JdbcChallengeIssuer`
- `JdbcDeviceRegistryStore`
- `JdbcSessionStore`
- `JdbcAuditSink`
- server-side persisted device, challenge, session and audit state
- atomic challenge replay protection using conditional `UPDATE`
- persisted nonce/fingerprint/token-hash integrity validation
- session token hash uniqueness
- V1 challenge, V2 session, V3 device and V4 audit migrations
- canonical schema includes device, challenge, session and audit tables
- active-expiry/state indexes
- environment-driven PostgreSQL configuration with TLS and channel binding required
- bounded connection and socket timeouts

### Session security

- opaque 256-bit bearer session credentials
- raw token returned only at issuance
- SHA-256 token digest persisted instead of the raw token
- bounded session lifetime (maximum 30 days)
- expiry and revocation checks
- malformed-token rejection
- session-store failures fail closed
- PostgreSQL persistence implementation
- revocation API foundation
- unit regression coverage for issue/authenticate/expiry/revocation/malformed/store-failure paths

### Runnable server foundation

- standalone JVM `server` module
- localhost-by-default binding
- bounded request body size
- health endpoint
- registration endpoint
- bootstrap-token-protected activation endpoint
- server-issued challenge endpoint
- challenge proof verification endpoint
- bearer-session revocation endpoint
- no raw database credentials in source
- no bearer token logging

### Engineering / supply chain

- GitHub Actions build/test/lint workflow
- APK SHA-256 checksum artifact
- CodeQL analysis workflow
- Dependabot for Gradle and GitHub Actions
- `.gitignore` for build, IDE, backup and signing material
- security policy
- durable state and traceability documentation

## Intentionally not accepted as complete

- production TLS termination/API gateway configuration
- transactional coupling of challenge consumption and mandatory audit persistence
- session rotation
- production revocation enforcement across every protected operation
- recovery/key rotation
- formal authorization middleware on every HTTP protected operation
- PostgreSQL integration execution evidence
- client ↔ server end-to-end authentication tests
- Android instrumentation on real/emulated devices
- performance benchmarks
- chaos/failure-injection tests
- production release signing and artifact verification
- repository-level GitHub Advanced Security enforcement if CodeQL is expected to be a required check

Interfaces and domain code do not count as production acceptance until execution evidence exists.

## Evidence status

- Source inspection: current modernization branch
- Latest Android CI: must be rechecked after latest server/database changes
- Latest CodeQL: must be rechecked after latest server/database changes
- Runtime Android identity verification: not yet performed
- PostgreSQL integration execution: not yet performed
- End-to-end authentication: not yet performed
- Performance benchmark: not performed
- Chaos testing: not performed

## Security acceptance matrix

- unknown/unbound device → DENY
- invalid signature → DENY
- modified client challenge data → DENY
- unknown challenge → DENY
- expired challenge → DENY
- replayed challenge → DENY
- device/key mismatch → DENY
- non-P256 key → DENY
- challenge-store failure → DENY
- malformed authorization request → DENY
- oversized authorization input → DENY
- missing role → DENY
- missing permission → DENY
- scope mismatch → DENY
- invalid/expired entitlement → DENY
- policy denial/exception → DENY
- invalid context → DENY
- audit persistence failure → DENY
- expired/revoked session → DENY
- revoked device → DENY
- valid bound device + valid authorization context → ALLOW

## Next vertical slice

Run/verify the new server against PostgreSQL → wire authorization middleware into protected operations → transactional audit/challenge boundary → session rotation → revocation enforcement → recovery/key rotation → Android client API integration → E2E → performance → chaos → release verification.

## Continuity rule

Missing context is `UNKNOWN`, never `PASS`. GitHub state takes precedence over chat summaries.
