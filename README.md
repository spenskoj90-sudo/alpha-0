# SENTINEL Alpha-0

Alpha-0 is the Android client and server-side security foundation for SENTINEL.
The implementation is intentionally split so that the client can prove possession
of a device key, while Sentinel Core remains the authoritative authorization boundary.

## Current release

**0.3.0 — foundation hardening**

### Implemented in source

**Android client**

- Android application shell
- Android Keystore-backed P-256 (`secp256r1`) device identity
- ECDSA `SHA256withECDSA` challenge signing and local verification
- SHA-256 public-key fingerprint generation
- Deterministic lowercase hexadecimal encoding with unit tests
- Runtime cryptographic self-test on application startup
- Explicitly disabled cleartext traffic
- Explicitly disabled backup/device-transfer extraction
- Debug builds do not require production release-signing secrets

**Sentinel Core**

- Centralized Default Deny authorization engine
- Required Role + Permission + Scope + Entitlement + Policy + Context evaluation
- Versioned scope rules
- Fail-closed malformed-input handling
- Fail-closed policy evaluation errors
- Server-side P-256 challenge/signature verification boundary
- Challenge replay-guard interface with atomic-consume contract
- Device fingerprint binding for server-issued challenges
- Mandatory audit-sink contract for successful security decisions
- Unit coverage for positive, negative, boundary, replay, substitution, and audit-failure cases

**Engineering / supply chain**

- Gradle build/test/lint CI
- APK SHA-256 checksum artifact
- CodeQL static analysis
- Dependency vulnerability review
- Dependabot for Gradle and GitHub Actions updates
- Durable Sentinel state and traceability documentation

## Intentionally not claimed as complete

The following still require production infrastructure and runtime evidence before Alpha RC acceptance:

- HTTP/API transport layer
- Persistent PostgreSQL repositories
- Production challenge store / replay guard implementation
- Device enrollment and explicit device-binding approval workflow
- Session lifecycle and token management
- Device revocation
- Recovery flows
- Network resilience / VPN integration
- Production release-signing pipeline and release artifact verification
- Android instrumentation tests on physical/emulated devices
- End-to-end client ↔ server authentication tests
- Performance and chaos benchmarks

These are not treated as implemented merely because domain interfaces exist.

## Security invariants

1. Unknown or unbound device → **DENY**
2. Invalid signature → **DENY**
3. Modified challenge → **DENY**
4. Replayed challenge → **DENY**
5. Device/key mismatch → **DENY**
6. Missing role → **DENY**
7. Missing permission → **DENY**
8. Scope mismatch → **DENY**
9. Invalid/expired entitlement → **DENY**
10. Policy failure or exception → **DENY**
11. Invalid context → **DENY**
12. Mandatory audit failure → **DENY**
13. Client-side state never overrides server-side authorization

## Acceptance rule

Source code is not considered accepted merely because it exists or compiles. SENTINEL uses:

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

Runtime/build/test/security claims require actual execution evidence.

## CI validation

The Android CI workflow validates:

1. `assembleDebug`
2. JVM unit tests for all modules
3. Android Lint
4. APK existence
5. APK SHA-256 checksum generation
6. Debug APK artifact publication

Additional security workflows perform CodeQL analysis and dependency vulnerability review.

A successful CI run is evidence for the configured checks only; it does not by itself establish production security, device-runtime acceptance, server deployment readiness, or Minimal Alpha RC readiness.

## Security notes

Device private keys are generated and stored by Android Keystore and are not exported by the application. The client is not the authoritative authorization boundary. Sentinel Core is the single source of truth for authorization.

Server-side challenge verification proves cryptographic possession only. Device binding, entitlement, authorization, revocation, and policy decisions remain separate server-side controls.

Production signing credentials must be supplied through CI secrets and must never be committed to the repository.
