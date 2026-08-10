# SENTINEL — Alpha-0 Traceability Map

This map records the current implementation-to-contract boundary. `Implemented` means source exists; `Accepted` requires execution evidence.

| Requirement | Current implementation | Source status | Acceptance status |
|---|---|---|---|
| Android client shell | `app` | Implemented | Pending runtime/build evidence |
| Device identity | `security/DeviceIdentity.kt` | Implemented | Pending runtime verification |
| Android Keystore | `DeviceIdentity` | Implemented | Pending runtime verification |
| P-256 / secp256r1 | `DeviceIdentity` | Implemented | Pending runtime verification |
| SHA-256 fingerprint | `DeviceIdentity` | Implemented | Unit coverage present; execution evidence pending |
| ECDSA sign/verify | `DeviceIdentity` | Implemented | Device/instrumentation verification pending |
| Deterministic hex | `security/Hex.kt` | Implemented | Unit coverage present; execution evidence pending |
| Default Deny | Server authorization | Not implemented | Not applicable |
| Least Privilege | Server authorization | Not implemented | Not applicable |
| RBAC + Scope | Authorization engine | Not implemented | Not applicable |
| Entitlement-aware access | Authorization engine | Not implemented | Not applicable |
| Policy-aware authorization | Authorization engine | Not implemented | Not applicable |
| Context-aware authorization | Authorization engine | Not implemented | Not applicable |
| Centralized authorization truth | Sentinel Core | Not implemented | Not applicable |
| Auditability | Core persistence/audit | Not implemented | Not applicable |
| PostgreSQL persistence | Sentinel Core | Not implemented | Not applicable |
| Device registration | Backend | Not implemented | Not applicable |
| Device binding | Backend | Not implemented | Not applicable |
| Server challenge verification | Backend | Not implemented | Not applicable |

## Verification classes

The accepted Test Matrix v1 requires positive, negative, security, failure, recovery, compatibility, performance, and chaos coverage as the implementation grows.

## Acceptance rule

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

No source-only claim is treated as runtime PASS.
