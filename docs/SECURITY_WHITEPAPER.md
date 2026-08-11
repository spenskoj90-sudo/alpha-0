# SENTINEL Security Whitepaper

## Threat model

SENTINEL assumes hostile clients, compromised game adapters, stolen session material, replay attempts, malformed events, privilege escalation attempts and untrusted AI output. It does not assume that local application state is authoritative.

## Trust boundaries

1. Android/web client → API edge
2. API edge → SENTINEL CORE
3. Core → PostgreSQL
4. Core → workers/outbox
5. Core → optional external AI/telemetry providers

The most important boundary is client → Core. Authorization is evaluated again on every privileged operation.

## Device identity

Android generates an EC P-256 key in Android Keystore. The private key is non-exportable by design. The server registers the public key and SHA-256 fingerprint. Device proofs sign a fresh server challenge plus timestamp and request id. Android's official `KeyGenParameterSpec` API supports EC key generation and signing restrictions; the Android documentation explicitly demonstrates NIST P-256/secp256r1 with SHA-256. 

## Replay resistance

Challenges are random, short-lived and single-use. Requests outside the clock-skew window are denied. Game events have unique IDs and monotonic per-device sequences. Server-side uniqueness is authoritative.

## Authorization

The engine is default-deny. A request needs a matching allow policy, required roles and required scopes. Explicit deny rules win. Entitlement and billing state are not permission substitutes; the authorization layer decides whether a specific action is permitted.

## AI safety

AI can summarize, infer and recommend. It cannot grant permission, mutate billing, revoke security state or issue privileged commands. Every recommendation carries confidence and provenance.

## Audit

Security decisions, device proof failures, event ingestion and other sensitive operations produce append-only audit events. Audit data is separate from telemetry and must not be deleted as part of normal application behavior.
