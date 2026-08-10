# ALPHA-0

ALPHA-0 is an Android client foundation focused on device identity and secure challenge signing.

## Current release

**0.3.0 — modernization pass**

### Implemented

- Android application shell
- Android Keystore-backed device identity
- P-256 / ECDSA challenge signing
- Public-key fingerprint generation
- Deterministic hex encoding with unit tests
- CI build, unit tests, Android Lint, and debug APK artifact
- Debug builds no longer depend on production signing secrets

### Not implemented yet

- Device registration / backend API
- Device binding and server-side verification
- Session management
- Device revocation
- VPN/network resilience
- Recovery flows
- Production release signing pipeline
- End-to-end authentication tests against a backend

## Build validation

The repository treats implementation as complete only after validation:

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

CI currently validates:

1. `assembleDebug`
2. JVM unit tests
3. `lintDebug`
4. Debug APK artifact creation

## Security notes

Device private keys are generated and stored by Android Keystore. Production signing credentials must be supplied through CI secrets and must never be committed to the repository.
