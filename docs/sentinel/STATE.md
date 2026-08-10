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

### Sentinel Core foundation

- Kotlin/JVM `core` module
- centralized Default Deny authorization engine
- explicit required-role membership
- permission check independent from role
- versioned scope ruleset with structural validation
- entitlement status/time-window evaluation
- policy evaluation with fail-closed exceptions
- context validation
- explicit `ALLOW` / typed `DENY` decisions
- bounded authorization inputs to reduce memory/CPU abuse
- server-side P-256 challenge/signature verification boundary
- trusted server-issued challenge-state lookup
- challenge expiry enforcement
- bounded challenge/public-key/signature inputs
- atomic challenge-consume contract for replay prevention
- server-issued expected-fingerprint binding with constant-time comparison
- mandatory audit-sink contract for security-success acknowledgement
- regression tests for positive, negative, boundary, replay, substitution, challenge-tampering, expiry, resource-limit and audit-failure paths

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
- PostgreSQL persistence
- production challenge store / atomic replay implementation
- explicit device enrollment and binding approval workflow
- session/token lifecycle
- revocation
- recovery
- network/VPN resilience
- production release signing and artifact verification
- Android instrumentation on real/emulated devices
- client ↔ server end-to-end authentication tests
- performance and chaos benchmarks

Interfaces and domain code do not count as production implementation until execution evidence exists.

## Evidence status

- Source inspection: verified on modernization branch
- CI: must be checked against the latest head after changes
- Runtime Android identity verification: not yet performed
- Server integration verification: not yet performed
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

Device Registration → Server Challenge Store → Server Challenge Verification → Device Binding Approval → PostgreSQL Persistence → Audit → protected operation through Core Authorization.

## Continuity rule

Missing context is `UNKNOWN`, never `PASS`. GitHub state takes precedence over chat summaries.
