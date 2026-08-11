# SENTINEL Diagrams

## Overall architecture

```mermaid
flowchart TB
    A[Android Launcher] -->|TLS /api/v1| C[SENTINEL CORE]
    W[Web Cabinet] -->|TLS /api/v1| C
    G[Game Adapters] -->|validated events| C
    C --> I[Identity + Authentication]
    C --> Z[Authorization Engine]
    C --> E[Entitlement Engine]
    C --> B[Billing Adapter]
    C --> GS[Game State]
    C --> K[Knowledge Engine]
    C --> EV[Event Store]
    C --> AU[Audit]
    C --> T[Telemetry]
    C --> DB[(PostgreSQL)]
    WK[Worker Manager] --> DB
    EV --> WK
    WK --> K
    WK --> AU
    WK --> T
```

## Authorization flow

```mermaid
sequenceDiagram
    participant D as Device/Browser
    participant API as SENTINEL CORE
    participant AUTH as Authentication
    participant Z as Authorization
    participant DB as PostgreSQL

    D->>API: Request + session token
    API->>AUTH: Validate session
    AUTH->>DB: Load session/device/user
    DB-->>AUTH: Session context
    AUTH-->>API: Authenticated principal
    API->>Z: authorize(action, resource, context)
    Z->>DB: Load roles/scopes/policies/ownership
    DB-->>Z: Authorization facts
    Z-->>API: ALLOW or DENY
    API->>DB: Mutate only after ALLOW
    API-->>D: Response
```

## Device identity

```mermaid
sequenceDiagram
    participant A as Android
    participant K as Android Keystore
    participant S as SENTINEL CORE
    participant DB as PostgreSQL

    A->>K: Generate EC P-256 key
    K-->>A: Public key; private key stays hardware/keystore-backed
    A->>S: Register public key + fingerprint
    S->>DB: Store device + key state ACTIVE
    A->>S: Request challenge
    S->>DB: Create one-time nonce
    S-->>A: challenge + expiry
    A->>K: Sign challenge
    K-->>A: ECDSA signature
    A->>S: challenge + signature + device id
    S->>DB: Atomically consume challenge
    S->>K: Verify public key signature
    S->>DB: Issue backend session
    S-->>A: session
```

## Game adapter / local-first flow

```mermaid
flowchart LR
    G[Game Process/API] --> AD[Adapter]
    AD --> V[Validate + Normalize]
    V --> Q[Local Durable Queue]
    Q --> UI[Local Character State]
    Q --> SYNC[Sync Worker]
    SYNC --> CORE[SENTINEL CORE]
    CORE --> EV[Domain Event Store]
    EV --> PROJ[State Projection]
    PROJ --> CORE
    CORE --> SYNC
    SYNC --> UI
```

## Event processing

```mermaid
flowchart TD
    CMD[API Command] --> TX[DB Transaction]
    TX --> AGG[Aggregate Mutation]
    AGG --> OUT[Outbox/Event Row]
    OUT --> POLL[Worker Poller]
    POLL --> LOCK[Claim with row lock]
    LOCK --> H[Idempotent Handler]
    H --> OK{Success?}
    OK -->|yes| DONE[Mark processed]
    OK -->|retryable| RETRY[Bounded retry/backoff]
    OK -->|permanent| DLQ[Dead-letter]
    RETRY --> POLL
```
