# SENTINEL Full-Stack Architecture v4

## 1. Scope

SENTINEL is a security-first modular monolith. `SENTINEL CORE` is the single source of truth for identity, authentication, authorization, entitlement, billing state, game state, knowledge, audit, and telemetry contracts.

The first production topology is deliberately small:

- Android client / launcher
- Web personal cabinet
- SENTINEL CORE API
- Background worker pool
- PostgreSQL
- Optional external billing provider adapter
- Optional game adapters
- Optional telemetry sink

No client is authoritative for authorization, entitlement, billing, or durable game state.

## 2. Module boundaries

| Module | Owns | Must not own |
|---|---|---|
| Identity | users, device records, public keys | permissions decisions |
| Authentication | challenges, signed proof, session issuance | entitlements |
| Authorization | roles, scopes, policies, allow/deny decisions | passwords/billing |
| Entitlement | grants, plan state, feature access | payment collection |
| Billing | provider references, invoices, subscription lifecycle | authorization policy |
| Game State | characters, snapshots, versioned state | identity keys |
| Knowledge | facts, sources, confidence, recommendations | authoritative state mutation |
| Events | immutable domain events, idempotency | business ownership |
| Audit | security and administrative audit trail | application logs |
| Telemetry | operational/product metrics | security decisions |
| Workers | retries, projections, async jobs | direct client trust |

## 3. Trust boundaries

1. Android device -> public API: untrusted network and untrusted client input.
2. Web browser -> public API: untrusted network and untrusted client input.
3. API -> PostgreSQL: trusted service boundary with least-privilege DB role.
4. Worker -> PostgreSQL: trusted internal service boundary.
5. External billing provider -> billing adapter: untrusted webhook input, verified by provider signature.
6. Game adapter -> core event ingress: treated as untrusted input and validated against adapter/game scope.

## 4. Security model

Every protected request follows:

`transport authentication -> session validation -> identity -> entitlement -> RBAC -> scope -> policy -> resource ownership -> action`

Default decision is DENY. Authorization is evaluated server-side. Client-side checks are UX only.

Device identity uses an Android Keystore EC P-256 key. The server stores the public key and SHA-256 fingerprint. Private keys never leave the device.

Replay protection uses a one-time server challenge with expiry, nonce binding, and request/session binding. Challenges are consumed atomically.

## 5. Event model

Domain events are append-only and carry:

- event id
- aggregate type/id
- event type
- schema version
- actor/user/device/session
- correlation id
- idempotency key
- event timestamp
- JSON payload

Consumers must be idempotent. Event processing is at-least-once; business handlers enforce deduplication.

## 6. Data ownership

PostgreSQL is authoritative. Redis/cache is intentionally not required for correctness. If introduced later, it remains a performance layer only.

## 7. Failure posture

- Fail closed for authorization.
- Fail closed for device verification.
- Never silently downgrade a cryptographic algorithm.
- Never accept expired/reused challenges.
- Never process duplicate idempotency keys twice.
- Preserve audit records on business failures.
- Queue retryable work with bounded exponential backoff.
- Dead-letter permanently failing jobs instead of infinite retry.

## 8. Deployment topology

For Alpha/production-minimal:

`Internet -> TLS reverse proxy -> SENTINEL CORE -> PostgreSQL`

Workers run beside CORE but use separate credentials. Android and web clients only see the public API. Administrative database access is never exposed to clients.

## 9. API versioning

Public routes are namespaced under `/api/v1`. Breaking changes require a new major API version. Event schemas use independent integer schema versions.

## 10. Acceptance gates

A component is ACCEPTED only after:

`implementation -> build -> unit tests -> integration tests -> security tests -> regression -> CI PASS`

A design document alone is never considered implementation.
