# SENTINEL — Alpha-0 Traceability Map

This map records the current implementation-to-contract boundary. `Implemented` means source exists; `Accepted` requires execution evidence.

| Requirement | Current implementation | Source status | Acceptance status |
|---|---|---|---|
| Android client shell | `app` | Implemented | CI + runtime evidence pending |
| Device identity | `security/DeviceIdentity.kt` | Implemented | Runtime verification pending |
| Android Keystore | `DeviceIdentity` | Implemented | Runtime verification pending |
| P-256 / secp256r1 | `DeviceIdentity` | Implemented | Runtime verification pending |
| SHA-256 fingerprint | `DeviceIdentity` | Implemented | Unit + CI execution evidence pending |
| ECDSA sign/verify | `DeviceIdentity` | Implemented | Runtime/instrumentation verification pending |
| Deterministic hex | `security/Hex.kt` | Implemented | Unit + CI execution evidence pending |
| Explicit role membership | `core/.../Authorization.kt` | Implemented | Core CI execution evidence pending |
| Permission independent from role | `Authorization.kt` | Implemented | Core CI execution evidence pending |
| Versioned Scope ruleset | `Authorization.kt` | Implemented | Core CI execution evidence pending |
| Entitlement status/time window | `Authorization.kt` | Implemented | Core CI execution evidence pending |
| Policy evaluation | `Authorization.kt` | Implemented | Core CI execution evidence pending |
| Context validation | `Authorization.kt` | Implemented | Core CI execution evidence pending |
| Authorization resource limits | `Authorization.kt` | Implemented | Core CI execution evidence pending |
| Default Deny decision paths | `Authorization.kt` + `AuthorizationMiddleware.kt` | Implemented | Core/server execution evidence pending |
| Least Privilege | Core authorization contract | Implemented foundation | Runtime/profile integration evidence pending |
| Server-side challenge verification | `DeviceChallengeVerifier.kt` | Implemented | Server E2E PASS on prior head; latest rerun pending |
| Trusted challenge state | `ChallengeStore` + `JdbcChallengeStore` | Implemented | PostgreSQL runtime verification pending on latest head |
| Challenge expiry | `DeviceChallengeVerifier` + DB schema | Implemented | PostgreSQL/runtime verification pending on latest head |
| Challenge replay protection | atomic `UPDATE ... consumed_at` | Implemented | PostgreSQL runtime verification pending on latest head |
| Device fingerprint binding | `BoundDeviceChallengeVerifier` + server-issued challenge state | Implemented | Server E2E PASS on prior head; latest rerun pending |
| Exact secp256r1 parameter enforcement | `DeviceChallengeVerifier` | Implemented | Core CI execution evidence pending |
| Constant-time fingerprint comparison | `MessageDigest.isEqual` | Implemented | Core CI execution evidence pending |
| Bounded cryptographic inputs | `DeviceChallengeVerifier` | Implemented | Core CI execution evidence pending |
| Mandatory auditability | `AuditSink` + `JdbcAuditSink` | Implemented | Durable runtime evidence pending |
| Audit failure → deny | `DeviceChallengeVerifier` + `AuthorizationMiddleware` | Implemented | Core/server execution evidence pending |
| Centralized authorization truth | Sentinel Core | Implemented foundation + server middleware | Protected endpoint evidence pending on latest head |
| Session credentials | `SessionManager` | Implemented | Core CI execution evidence pending |
| Session token storage | SHA-256 digest of opaque token + `JdbcSessionStore` | Implemented | PostgreSQL runtime verification pending |
| Session expiry | `SessionManager` | Implemented | Core CI execution evidence pending |
| Session revocation | `SessionManager` + `JdbcSessionStore` | Implemented | Server E2E PASS on prior head; latest rerun pending |
| Device registration | `DeviceRegistry` + `/v1/devices/register` | Implemented | Server E2E PASS on prior head; latest rerun pending |
| Device binding approval | `DeviceRegistry.activate` + enrollment-token protected endpoint | Implemented | Server E2E PASS on prior head; latest rerun pending |
| PostgreSQL persistence | devices/challenges/sessions/audit/recovery + migrations | Implemented | Latest integration/deployment evidence pending |
| Session rotation | `SessionRotator` + `/v1/sessions/rotate` | Implemented | Server E2E PASS on prior head; latest rerun pending |
| Device revocation | `DeviceRegistry` state model | Implemented domain capability | External/admin integration endpoint still required |
| Recovery / key rotation | `DeviceRecoveryService` + PostgreSQL atomic rotation | Implemented | Server E2E PASS on prior head; latest rerun pending |
| Network/VPN resilience | Client/backend | Not implemented | Not accepted |
| End-to-end authentication | Client/server protocol + `scripts/server-e2e.sh` | Implemented | Server E2E PASS on prior head; latest rerun pending |
| Performance | `SecurityStressTest` only | Partial test infrastructure | Measured target-environment benchmark not accepted |
| Chaos/failure injection | fail-closed regression/stress coverage | Partial test infrastructure | Real dependency/service chaos not accepted |

## Current CI evidence

- CodeQL: PASS on previous implementation head; latest head is running.
- Android build: PASS on previous implementation head; latest head is running.
- Server E2E: PASS on previous implementation head; latest head is running.
- Release artifact verification: PASS on previous implementation head.
- Security regression + bounded stress: PASS on previous implementation head.
- Dependency Review: BLOCKED by GitHub repository configuration because Dependency Graph is disabled. This is not being bypassed or downgraded.
- Latest discovered compile defect: server test source imported JUnit Jupiter without a server test dependency. Fixed in commit `ba6547506dcfffc8d901655025d9c93f8b7557f4`; verification is in progress.

## Verification classes

The accepted Test Matrix v1 requires positive, negative, security, failure, recovery, compatibility, performance, and chaos coverage as the implementation grows.

## Acceptance rule

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`

No source-only claim is treated as runtime PASS.
