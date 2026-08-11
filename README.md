# SENTINEL Alpha-0

Alpha-0 is the Android client and server-side security foundation for SENTINEL.
The implementation is intentionally split so that the client can prove possession
of a device key, while Sentinel Core remains the authoritative authorization boundary.

## Current release

**0.3.0 — security-hardened runnable vertical slice**

## Implemented

### Android client

- Android Keystore-backed P-256 (`secp256r1`) device identity
- ECDSA `SHA256withECDSA` challenge signing and local verification
- SHA-256 public-key fingerprint generation
- deterministic lowercase hexadecimal encoding with unit tests
- runtime cryptographic self-test on application startup
- explicit cleartext-traffic prohibition
- explicit backup/device-transfer exclusion
- debug CI builds do not require production release-signing secrets

### Sentinel Core

- centralized Default Deny authorization engine
- Role + Permission + Scope + Entitlement + Policy + Context evaluation
- versioned scope rules
- bounded inputs and fail-closed malformed-input handling
- fail-closed policy evaluation errors
- server-side P-256 challenge/signature verification boundary
- trusted server-side challenge-state lookup and atomic consume contract
- device fingerprint binding for server-issued challenges
- client cannot replace the server-issued challenge nonce or identity context
- mandatory audit-sink contract for security-sensitive decisions
- session expiry/revocation/rotation
- recovery-code hashing and atomic device key rotation

### Server / persistence

- runnable JVM server
- device registration and explicit activation
- server-issued challenges and proof verification
- PostgreSQL persistence for devices, recovery codes, challenges, sessions and audit events
- PostgreSQL TLS + channel-binding enforcement
- protected authorization endpoint
- bounded request bodies/form fields
- strict form content type
- duplicate parameter rejection
- bounded per-client rate limiting
- security response headers
- graceful shutdown
- no raw bearer-token logging

### Validation / supply chain

- Android build/test/lint CI
- Android emulator instrumentation
- Server + PostgreSQL E2E
- CodeQL
- Dependabot
- dependency review
- security regression tests
- bounded security stress tests
- failure-closed regression coverage
- signed release workflow with APK signature and SHA-256 verification

## Public repository security

This repository is public. Production credentials, signing keys and deployment secrets are never part of the source tree. Public pull-request CI is designed to operate without production signing secrets. Release signing is isolated to the tag/manual release workflow.

GitHub secret scanning runs automatically for public repositories. Push protection should remain enabled; never bypass a secret-detection block unless the value has been independently verified to be non-sensitive.

## Intentionally not claimed as complete

Runtime acceptance and production deployment still require evidence for:

- latest GitHub Actions validation on the final head;
- production PostgreSQL configuration and certificates;
- production API gateway/TLS termination;
- production release-signing secrets and artifact publication;
- supported physical-device/emulator acceptance matrix;
- measured performance benchmarks in a defined target environment;
- production operational monitoring and recovery procedures.

These are execution/deployment gates, not reasons to weaken the accepted Sentinel architecture.

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

Source code is not considered accepted merely because it exists or compiles.

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

Runtime/build/test/security claims require actual execution evidence.
