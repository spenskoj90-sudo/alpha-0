# SENTINEL Alpha-0

Alpha-0 is the Android client foundation for SENTINEL. The current client scope is deliberately limited to device identity and secure challenge signing.

## Current release

**0.3.0 — Android foundation hardening**

### Implemented in source

- Android application shell
- Android Keystore-backed device identity
- P-256 (`secp256r1`) key material
- ECDSA `SHA256withECDSA` challenge signing and local verification
- SHA-256 public-key fingerprint generation
- Deterministic lowercase hexadecimal encoding with unit tests
- CI build, JVM unit tests, Android Lint, and debug APK artifact validation
- Debug builds do not require production release-signing secrets

### Not implemented yet

- Device registration / backend API
- Server-side device binding and signature verification
- Session management
- Device revocation
- Sentinel Core / PostgreSQL persistence
- Server-side authorization (RBAC + Scope + Entitlement + Policy + Context)
- Audit persistence
- VPN/network resilience
- Recovery flows
- Production release signing pipeline
- End-to-end authentication tests against a backend

## Acceptance rule

Source code is not considered accepted merely because it exists or compiles. SENTINEL uses:

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

Runtime/build/test claims require actual execution evidence.

## CI validation

The Android CI workflow validates:

1. `assembleDebug`
2. JVM unit tests
3. `lintDebug`
4. Debug APK existence
5. Debug APK artifact publication

A successful CI run is evidence for the configured checks only; it does not by itself establish server-side security acceptance or Minimal Alpha RC readiness.

## Security notes

Device private keys are generated and stored by Android Keystore. The client is not the authoritative authorization boundary. Server-side authorization will be implemented separately in the Sentinel Core and must enforce the accepted Default Deny / Least Privilege / RBAC + Scope / Entitlement / Policy / Context contract.

Production signing credentials must be supplied through CI secrets and must never be committed to the repository.
