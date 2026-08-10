# SENTINEL — Alpha-0 Traceability Map

This map records the current implementation-to-contract boundary. `Implemented` means source exists; `Accepted` requires execution evidence.

| Requirement | Current implementation | Source status | Acceptance status |
|---|---|---|---|
| Android client shell | `app` | Implemented | CI + runtime evidence pending |
| Device identity | `security/DeviceIdentity.kt` | Implemented | Runtime verification pending |
| Android Keystore | `DeviceIdentity` | Implemented | Runtime verification pending |
| P-256 / secp256r1 | `DeviceIdentity` | Implemented | Runtime verification pending |
| SHA-256 fingerprint | `DeviceIdentity` | Implemented | Unit coverage present; CI execution pending |
| ECDSA sign/verify | `DeviceIdentity` | Implemented | Runtime/instrumentation verification pending |
| Deterministic hex | `security/Hex.kt` | Implemented | Unit coverage present; CI execution pending |
| Explicit role membership | `core/.../Authorization.kt` | Implemented | Core CI execution pending |
| Permission independent from role | `Authorization.kt` | Implemented | Core CI execution pending |
| Versioned Scope ruleset | `Authorization.kt` | Implemented | Core CI execution pending |
| Entitlement status/time window | `Authorization.kt` | Implemented | Core CI execution pending |
| Policy evaluation | `Authorization.kt` | Implemented | Core CI execution pending |
| Context validation | `Authorization.kt` | Implemented | Core CI execution pending |
| Default Deny decision paths | `Authorization.kt` | Implemented in domain engine | Server enforcement pending |
| Least Privilege | Core authorization contract | Foundation implemented | Server enforcement pending |
| Server-side challenge verification | `core/.../DeviceChallengeVerifier.kt` | Implemented domain boundary | Integration/persistence pending |
| Challenge replay protection | `ChallengeReplayGuard` | Interface contract | Atomic persistent implementation pending |
| Device fingerprint binding | server-issued challenge context | Implemented domain boundary | Integration/persistence pending |
| Mandatory auditability | `AuditSink` | Interface contract | Durable persistence pending |
| Audit failure → deny | `DeviceChallengeVerifier` | Implemented | Core CI execution pending |
| Centralized authorization truth | Sentinel Core | Foundation implemented | API/service enforcement pending |
| Device registration | Backend | Not implemented | Not accepted |
| Device binding approval | Backend | Not implemented | Not accepted |
| PostgreSQL persistence | Sentinel Core | Not implemented | Not accepted |
| Session/token lifecycle | Backend | Not implemented | Not accepted |
| Device revocation | Backend | Not implemented | Not accepted |
| Recovery | Backend/client | Not implemented | Not accepted |
| Network/VPN resilience | Client/backend | Not implemented | Not accepted |
| End-to-end authentication | Client ↔ server | Not implemented | Not accepted |
| Performance | Test infrastructure | Not implemented | Not accepted |
| Chaos/failure injection | Test infrastructure | Not implemented | Not accepted |

## Verification classes

The accepted Test Matrix v1 requires positive, negative, security, failure, recovery, compatibility, performance, and chaos coverage as the implementation grows.

## Acceptance rule

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

No source-only claim is treated as runtime PASS.
