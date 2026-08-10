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

### Device challenge security

- server-side P-256 challenge/signature verification boundary
- client submits only challenge ID, public key and signature
- trusted server-issued nonce, expiry and expected fingerprint
- 32–64 byte challenge nonce bound
- bounded challenge ID, public-key and signature inputs
- P-256 enforcement
- challenge expiry before expensive cryptography
- expiry re-check immediately before atomic consumption
- atomic challenge-consume contract for replay prevention
- constant-time fingerprint comparison
- challenge-store failures fail closed
- mandatory audit acknowledgement for successful verification
- audit failure denies
- regression coverage for positive, negative, replay, substitution, expiry, malformed, oversized and storage-failure paths

### PostgreSQL persistence slice

- PostgreSQL JDBC 42.7.13
- `JdbcChallengeStore`
- server-side persisted challenge state
- atomic replay protection using conditional `UPDATE`
- persisted nonce/fingerprint integrity validation
- Flyway-style `V1__device_challenges.sql` migration
- active-expiry and consumed-state indexes

### Engineering / supply chain

- GitHub Actions build/test/lint workflow
- APK SHA-256 checksum artifact
- CodeQL analysis workflow
- Dependabot for Gradle and GitHub Actions
- `.gitignore` for build, IDE, backup and signing material
- security policy
- durable state and traceability documentation

## Intentionally not accepted as complete

- HTTP/API transport
- production device registration and binding approval workflow
- session/token lifecycle
- revocation
- recovery/key rotation
- production database operational configuration and migration execution evidence
- Android instrumentation on real/emulated devices
- client ↔ server end-to-end authentication tests
- performance benchmarks
- chaos/failure-injection tests
- production release signing and artifact verification
- repository-level GitHub Advanced Security enforcement if CodeQL is expected to be a required check

Interfaces and domain code do not count as production acceptance until execution evidence exists.

## Evidence status

- Source inspection: current modernization branch
- Latest Android CI: in progress for current head
- Latest CodeQL: queued for current head
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
- valid bound device + valid authorization context → ALLOW

## Next vertical slice

Device Registration → Binding Approval → Session/Token Lifecycle → Revocation → Recovery/Key Rotation → HTTP/API enforcement → PostgreSQL integration tests → Client/Server E2E → performance → chaos → release verification.

## Continuity rule

Missing context is `UNKNOWN`, never `PASS`. GitHub state takes precedence over chat summaries.
