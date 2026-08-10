# SENTINEL — Alpha-0 Security Audit

## Audit scope

This audit covers the current Alpha-0 modernization branch against the accepted Architecture v3 / Implementation Contract v1 / Test Matrix v1 baseline and the current source tree.

## Controls checked

| Area | Result | Evidence / boundary |
|---|---|---|
| Private-key storage | PASS at source level | Android Keystore-backed EC key |
| Private-key export | Runtime check implemented | Android crypto self-test |
| Signature algorithm | PASS at source level | P-256 / `SHA256withECDSA` |
| Fingerprint encoding | PASS at source + unit coverage | SHA-256 + deterministic lowercase hex |
| Challenge minimum size | PASS | 32-byte minimum |
| Challenge maximum size | PASS | 64-byte upper bound before crypto work |
| Trusted challenge state | PASS at domain boundary | nonce, expiry and expected fingerprint come only from `ChallengeStore` |
| Challenge expiry | PASS at domain boundary | verifier rejects expired challenges before signature work and re-checks before consume |
| Challenge replay | PASS at persistence boundary | `JdbcChallengeStore.consume()` uses one conditional atomic UPDATE; production execution evidence still pending |
| Identity substitution | PASS at domain level | fingerprint derived from submitted public key; expected fingerprint comes from trusted challenge state |
| Fingerprint comparison | PASS | constant-time byte comparison |
| Challenge tampering | PASS at domain level | client cannot replace server-issued nonce or identity context |
| Input resource bounds | PASS at domain boundary | bounded IDs, keys, signatures, roles, permissions, scope rules and context |
| Default Deny | PASS at domain level | explicit typed deny decisions |
| Role enforcement | PASS at domain level | required role must be present |
| Permission enforcement | PASS at domain level | resource/action permission required independently |
| Scope enforcement | PASS at domain level | versioned ruleset with structural validation |
| Entitlement | PASS at domain level | status + time-window validation |
| Policy exceptions | PASS | policy exceptions become DENY |
| Context validation | PASS | blank/oversized keys and values denied |
| Challenge-store failure | PASS | storage exceptions become typed DENY rather than escaping the security boundary |
| Audit requirement | PASS at domain boundary | successful verification requires audit acknowledgement |
| Audit failure | PASS | audit unavailable becomes DENY |
| Cleartext network | PASS | Android manifest + network security config |
| Backup/data transfer | PASS | disabled in manifest and extraction rules |
| CI build/test/lint | Automated | GitHub Actions; current head still running |
| Artifact integrity | Automated | APK SHA-256 checksum |
| Static analysis | Configured | CodeQL workflow; current head queued |
| Secrets in source | Guarded | `.gitignore`, CI secret-backed release signing |

## Release blockers

The following remain blockers for claiming a production-ready Minimal Alpha RC:

1. production API/transport implementation;
2. explicit device registration and binding approval;
3. session/token lifecycle;
4. server-side revocation;
5. recovery and key-rotation flows;
6. production PostgreSQL operational configuration and integration execution evidence;
7. end-to-end client/server authentication tests;
8. Android instrumentation on a real/emulated device;
9. performance evidence;
10. chaos/failure-injection evidence;
11. production release signing and artifact verification;
12. repository-level GitHub Advanced Security configuration if CodeQL is expected to be enforced as a required check.

## Acceptance rule

No source-only claim is promoted to PASS. Final acceptance remains:

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`
