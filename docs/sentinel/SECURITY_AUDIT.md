# SENTINEL — Alpha-0 Security Audit

## Audit scope

This audit covers the current Alpha-0 modernization branch against the accepted Architecture v3 / Implementation Contract v1 / Test Matrix v1 baseline and the current source tree.

## Controls checked

| Area | Result | Evidence / boundary |
|---|---|---|
| Private-key storage | PASS at source level | Android Keystore-backed EC key |
| Private-key export | Runtime check implemented | `DeviceIdentity.isPrivateKeyExported()` |
| Signature algorithm | PASS at source level | P-256 / `SHA256withECDSA` |
| Fingerprint encoding | PASS at source + unit coverage | SHA-256 + deterministic lowercase hex |
| Challenge minimum size | PASS | 32-byte minimum in server verifier |
| Challenge replay | Contract present | `ChallengeReplayGuard.consume()` must be atomic/persistent in production |
| Identity substitution | PASS at domain level | fingerprint derived from submitted public key; optional expected fingerprint binding |
| Default Deny | PASS at domain level | explicit typed deny decisions |
| Role enforcement | PASS at domain level | required role must be present |
| Permission enforcement | PASS at domain level | resource/action permission required independently |
| Scope enforcement | PASS at domain level | versioned ruleset with structural validation |
| Entitlement | PASS at domain level | status + time-window validation |
| Policy exceptions | PASS | policy exceptions become DENY |
| Context validation | PASS | blank keys/values denied |
| Audit requirement | PASS at domain boundary | successful verification requires audit acknowledgement |
| Audit failure | PASS | audit unavailable becomes DENY |
| Cleartext network | PASS | Android manifest + network security config |
| Backup/data transfer | PASS | disabled in manifest and extraction rules |
| CI build/test/lint | Automated | GitHub Actions |
| Artifact integrity | Automated | APK SHA-256 checksum |
| Static analysis | Configured | CodeQL workflow |
| Dependency updates | Configured | Dependabot |
| Secrets in source | Guarded | `.gitignore`, CI secret-backed release signing |

## Release blockers

The following remain blockers for claiming a production-ready Minimal Alpha RC:

1. production API/transport implementation;
2. persistent PostgreSQL storage;
3. atomic persistent challenge/replay store;
4. explicit device enrollment and binding approval;
5. server-side revocation;
6. session/token lifecycle;
7. recovery and key-rotation flows;
8. end-to-end client/server authentication tests;
9. Android instrumentation on a real/emulated device;
10. performance and chaos evidence;
11. production release signing and release artifact verification;
12. repository-level GitHub Advanced Security configuration if CodeQL/Dependency Review is expected to be enforced as a required check.

## Acceptance rule

No source-only claim is promoted to PASS. Final acceptance remains:

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`
