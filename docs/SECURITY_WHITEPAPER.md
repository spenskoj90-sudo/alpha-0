# SENTINEL Security Whitepaper — 1.0.0-RC1

## Threat model

SENTINEL assumes hostile clients, compromised game adapters, stolen session material, replay attempts, malformed events, object-level authorization attacks, privilege escalation attempts and untrusted AI output. Local application state is never treated as authoritative security truth.

## Trust boundaries

1. Android/web client → API edge
2. API edge → SENTINEL CORE
3. Core → PostgreSQL
4. Core → workers/outbox
5. Core → optional external AI/telemetry providers

The client → Core boundary is authoritative for security. Every privileged operation is re-authenticated at the server and evaluated by the centralized authorization path.

## Device identity

Android generates an EC P-256 (`secp256r1`) signing key in Android Keystore. The private key never leaves the Keystore API. The server stores the public key and SHA-256 fingerprint. Device proof signs canonical challenge data containing a fresh nonce, timestamp and request id.

Device enrollment is bound to a user-specific enrollment secret. Production startup fails closed when enrollment configuration is absent.

## Session security

SENTINEL uses high-entropy opaque access and refresh tokens rather than placing authorization state in client-controlled JWT claims. Only hashes of session tokens are persisted server-side. Access sessions expire; refresh tokens are rotated on every successful refresh and replay of an already-used refresh token is rejected.

The design follows the current OAuth security direction of sender-constrained or replay-resistant tokens for public clients. Where a future OAuth/DPoP surface is introduced, it must preserve the existing device-key binding rather than weakening it.

## Replay resistance

Challenges are random, short-lived and single-use. Requests outside the configured clock-skew window are denied. Game events have unique IDs, device binding, monotonic per-device sequences and idempotency keys. PostgreSQL uniqueness and transactional locking are authoritative for production event ordering.

## Authorization

The engine is default-deny. A request needs a matching allow policy and all required roles/scopes. Explicit deny rules win. Scope syntax and requested-scope composition are validated before authorization. Billing and entitlement state are inputs to business access rules but are never treated as direct permission grants.

## Input and error handling

API models reject unknown fields where appropriate and enforce bounded lengths and constrained identifiers. Validation failures use a stable error envelope. Unexpected exceptions return a generic internal error to clients; SQL errors, stack traces, credentials, tokens and signatures are not exposed in API responses or audit records.

## Rate limiting

Sensitive device and session surfaces use bounded request-rate controls. Production deployments should additionally enforce distributed rate limiting at the WAF/API edge when multiple Core replicas are used.

## Audit

Security decisions, device proof failures, session lifecycle events and event ingestion produce append-oriented audit records. Audit data is separate from telemetry and is never a source of authorization truth.

## AI safety

AI can summarize, infer and recommend. It cannot grant permission, mutate billing, revoke security state or issue privileged commands. Every recommendation carries confidence and provenance.

## Release integrity

A release candidate is not accepted merely because code exists. The exact commit must pass compile, unit, integration/security, migration and artifact gates. Any unavailable or unverified gate remains explicitly unverified.
