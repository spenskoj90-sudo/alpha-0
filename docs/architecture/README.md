# SENTINEL Full-Stack Architecture v4

## 1. System boundaries

SENTINEL CORE is the single source of truth for identity, authorization, entitlements, billing state, canonical game state, knowledge provenance, telemetry policy, and audit records.

Clients are untrusted. Android is local-first for gameplay adapters and offline UX, but server authorization is authoritative. The web client is a presentation client and never receives authorization to bypass Core policy.

## 2. Modules

- Identity: account and device identity records.
- Authentication: credential/session verification.
- Authorization: RBAC + scope + policy, default deny.
- Entitlement: derived access rights from grants/subscriptions.
- Billing: provider-neutral billing state and immutable ledger references.
- Game State: canonical character/game state and versioning.
- Knowledge: facts, inferences, recommendations, provenance and confidence.
- Telemetry: allowlisted events, privacy controls, rate limits.
- Eventing: transactional outbox, idempotency, consumer checkpoints.
- Workers: bounded background jobs with retry/backoff/dead-letter semantics.
- Audit: append-only security-sensitive trail.
- Session Protocol: short-lived server sessions bound to device identity and challenge-response.

## 3. Trust model

1. Network is hostile.
2. Client state is advisory and may be replayed or modified.
3. Server validates every privileged operation.
4. Every write has an actor, scope and idempotency key where applicable.
5. Security-sensitive records are append-only or versioned.
6. Database access is least privilege; tenant/user isolation uses PostgreSQL RLS where applicable.

## 4. Runtime topology

```mermaid
flowchart TB
  A[Android Launcher / App] -->|HTTPS + challenge response| C[SENTINEL CORE]
  W[Web Dashboard] -->|HTTPS + session| C
  G[Game Adapter SDK] -->|local events| A
  C --> I[Identity]
  C --> AU[Authorization Engine]
  C --> E[Entitlement Engine]
  C --> B[Billing Engine]
  C --> S[Session Protocol]
  C --> K[Knowledge Engine]
  C --> GS[Canonical Game State]
  C --> T[Telemetry Policy]
  C --> AD[Audit]
  C --> O[(PostgreSQL)]
  C --> Q[Transactional Outbox]
  Q --> WK[Worker Manager]
  WK --> EV[Event Consumers]
  EV --> K
  EV --> GS
  EV --> T
  EV --> AD
  C --> EXT[External Providers]
  EXT --> B
```

## 5. Authorization flow

```mermaid
sequenceDiagram
  participant D as Device
  participant C as Core
  participant A as AuthZ Engine
  participant DB as PostgreSQL
  D->>C: POST /v1/sessions/challenge
  C->>DB: create nonce + expiry
  DB-->>C: challenge
  C-->>D: challenge + session_id
  D->>C: POST /v1/sessions/verify (signature)
  C->>C: verify public key + signature + freshness
  C->>A: authorize session:create
  A->>DB: roles/scopes/policies/entitlements
  DB-->>A: decision inputs
  A-->>C: ALLOW/DENY
  C-->>D: short-lived session token
  D->>C: privileged request + token
  C->>A: authorize(actor, action, resource, scope)
  A-->>C: decision
  C->>DB: commit authorized change + audit/outbox
```

## 6. Device identity

```mermaid
sequenceDiagram
  participant A as Android
  participant K as Android Keystore
  participant C as Core
  A->>K: generate EC P-256 signing key
  K-->>A: public certificate
  A->>A: SHA-256(publicKey.encoded)
  A->>C: register device + public key + fingerprint
  C->>C: validate curve/algorithm/fingerprint
  C-->>A: device_id + lifecycle=ACTIVE
  C->>C: issue random challenge
  C-->>A: nonce + expires_at
  A->>K: sign(domain || nonce || request_hash)
  K-->>A: ECDSA signature
  A->>C: signature
  C->>C: verify signature + nonce + device lifecycle
  C-->>A: session
```

Android Keystore keeps private key material non-exportable and can bind keys to secure hardware; hardware-backed status and attestation must be treated as device properties, not as a replacement for server-side authorization. citeturn1search0turn1search1

## 7. Game adapter

```mermaid
flowchart LR
  GAME[Game / Adapter] --> L[Local Event Store]
  L --> UI[Character Dashboard]
  L --> Q[Offline Queue]
  Q --> SYNC[Sync Engine]
  SYNC -->|idempotent events| CORE[SENTINEL CORE]
  CORE -->|accepted canonical events| L
  CORE --> STATE[(Canonical Game State)]
  CORE --> OUT[Outbox]
  OUT --> CON[Consumers]
```

## 8. Event system

```mermaid
flowchart TB
  TX[Authorized transaction] --> DB[(PostgreSQL)]
  TX --> OB[Transactional Outbox]
  OB --> DISP[Dispatcher]
  DISP --> C1[Game State Consumer]
  DISP --> C2[Knowledge Consumer]
  DISP --> C3[Telemetry Consumer]
  DISP --> C4[Audit Consumer]
  C1 --> CK[Consumer Checkpoints]
  C2 --> CK
  C3 --> CK
  C4 --> CK
  DISP --> DLQ[Dead Letter Queue]
```

Exactly-once side effects are implemented as at-least-once delivery plus idempotent consumers. The outbox record and domain mutation are committed in one database transaction.

## 9. API layers

- `/v1/sessions/*`: challenge-response and session lifecycle.
- `/v1/devices/*`: device registration, rotation, revocation.
- `/v1/me/*`: user-scoped dashboard data.
- `/v1/characters/*`: canonical game state.
- `/v1/knowledge/*`: fact/inference/recommendation retrieval.
- `/v1/events/*`: authenticated client event ingestion.
- `/v1/billing/*`: provider-neutral billing state.
- `/v1/audit/*`: privileged audit views.
- `/health/live`, `/health/ready`: operational health only; no secrets.

## 10. Security invariants

- Missing authorization context => deny.
- Unknown action => deny.
- Unknown scope => deny.
- Revoked device => deny.
- Expired nonce => deny.
- Reused nonce => deny.
- Session expired/revoked => deny.
- Client-provided role/entitlement/billing fields are ignored.
- Audit records cannot be modified through public API.
- Sensitive telemetry is opt-in/allowlisted and minimized.
