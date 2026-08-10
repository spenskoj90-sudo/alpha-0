# SENTINEL — Alpha-0 Security Audit

## Scope

Architecture v3 / Implementation Contract v1 / Test Matrix v1 against the current Alpha-0 security vertical slice.

## Controls

| Control | Source status | Runtime gate |
|---|---|---|
| Android Keystore P-256 | PASS | emulator/device instrumentation |
| Non-exportable private key | PASS | emulator/device instrumentation |
| SHA-256 fingerprint | PASS | unit + E2E |
| ECDSA proof | PASS | unit + server E2E |
| Challenge nonce 32–64 bytes | PASS | unit + E2E |
| Exact secp256r1 enforcement | PASS | unit |
| Challenge expiry/replay | PASS | unit + E2E |
| Fingerprint constant-time comparison | PASS | unit |
| PENDING/ACTIVE/REVOKED binding | PASS | unit + E2E |
| Atomic challenge + audit | PASS | PostgreSQL E2E |
| Default Deny authorization | PASS | unit + protected endpoint E2E |
| Role/permission/scope/entitlement/policy/context | PASS | unit |
| Session hashing/expiry/revocation | PASS | unit + E2E |
| Atomic session rotation | PASS | unit + E2E |
| Recovery code hashing/expiry/one-time use | PASS | unit + E2E |
| Atomic key rotation | PASS | PostgreSQL E2E |
| PostgreSQL TLS/channel binding | PASS at config boundary | PostgreSQL E2E |
| Request/resource bounds | PASS | unit + server |
| Cleartext disabled | PASS | Android instrumentation |
| Backup/data-transfer disabled | PASS | Android configuration |
| CodeQL | configured | GitHub Actions |
| APK integrity | configured | release workflow |
| Production signing | configured | release secrets + workflow |

## Security architecture invariants

1. Registration never grants authorization.
2. Only server-issued challenge state is trusted.
3. Cryptographic proof is not itself authorization.
4. Revoked or inactive devices cannot authenticate.
5. Session credentials are opaque and only their SHA-256 digests are persisted.
6. Rotation invalidates the old credential atomically.
7. Recovery code consumption and key replacement are atomic.
8. Successful challenge proof and its mandatory audit event are committed atomically.
9. Authorization is server-side and fail-closed.
10. Production secrets/signing material are supplied only through runtime/CI secrets.

## Remaining acceptance gates

These are execution/deployment gates rather than missing core implementations:

- latest GitHub Actions runs must finish PASS;
- production API gateway/TLS termination must be configured and verified;
- production PostgreSQL deployment must be verified with the intended certificates/credentials;
- Android instrumentation must PASS on the supported device/emulator matrix;
- production release signing must PASS with repository secrets;
- production operational/monitoring configuration must be reviewed.

## Acceptance rule

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

No source-only claim is promoted to runtime PASS.
