# SENTINEL CORE API — Release Candidate

The running FastAPI service publishes the live API specification at `/openapi.json` and Swagger UI at `/docs`. This document is a concise manual index of the currently implemented routes; when in doubt, `/openapi.json` is the runtime source of truth.

## Public health

- `GET /healthz` — service health check.

## User authentication

- `POST /v1/auth/register` — create an account and issue a least-privilege user session.
- `POST /v1/auth/login` — authenticate an existing account and issue a least-privilege user session.
- `POST /v1/auth/email-verification/request` — non-enumerating request for a 24-hour one-time email-verification code.
- `POST /v1/auth/email-verification/confirm` — consume a verification code exactly once and mark the account email verified.
- `POST /v1/auth/password-reset/request` — non-enumerating request for a 30-minute one-time password-reset code.
- `POST /v1/auth/password-reset/confirm` — consume the reset code, replace the password and revoke all existing account sessions.
- `GET /v1/account/security` — caller-scoped email-verification/password/provider-link security state.
- `GET /v1/auth/providers` — public fail-closed provider capability catalog; exposes enablement/flow/public client ID only, never provider secrets.
- `POST /v1/auth/providers/google/challenge` — issue a one-time server nonce for Credential Manager Google ID-token authentication.
- `POST /v1/auth/providers/google/login` — verify a nonce-bound Google ID token server-side and issue a SENTINEL session.
- `POST /v1/auth/providers/{telegram|vk}/start` — validate an exact allowlisted callback URI, persist a hashed one-time state and return the provider authorization URL plus PKCE verifier.
- `POST /v1/auth/providers/{telegram|vk}/complete` — consume the state, perform the server-side code exchange and issue a SENTINEL session.
- `POST /v1/account/providers/google/link` and `POST /v1/account/providers/{telegram|vk}/link` — require an existing SENTINEL Bearer session plus a fresh provider proof to add another sign-in identity.

## Device identity

- `POST /v1/devices/register` — register a device with a public-key fingerprint; supports authenticated user-bound enrollment and the legacy enrollment-token bootstrap path.
- `POST /v1/devices/bind` — bind a new device key to the authenticated user session and return the first one-time proof challenge.
- `GET /v1/devices/{device_id}` — read the caller-owned device state.
- `POST /v1/devices/{device_id}/challenge` — issue a fresh one-time proof challenge for a caller-owned active device; used for proof retry without creating another device binding.
- `POST /v1/devices/{device_id}/prove` — consume the device challenge and verify a P-256 signed proof to issue a device-bound session.
- `POST /v1/devices/{device_id}/rotate` — rotate a caller-owned active device key and issue a new device-bound session.
- `POST /v1/devices/{device_id}/revoke` — revoke a caller-owned device and its sessions.

## Sessions

- `POST /v1/sessions/refresh` — one-time refresh-token rotation.
- `POST /v1/sessions/revoke` — revoke the current access session.

## Authorization and events

- `POST /v1/authorize` — server-side default-deny authorization decision.
- `POST /v1/events:batch` — authenticated event-batch ingestion with sequence and idempotency protections. Event writes require a device-bound session carrying `game:write`; ordinary login/register sessions intentionally do not carry that scope.
- `GET /v1/audit` — caller-scoped audit history.

Accepted character events are projected into the character store on a best-effort basis after durable event acceptance. Public clients do not receive a direct mutable character-write endpoint.

## Integrity

- `POST /v1/integrity/nonce` — issue a short-lived server nonce for integrity attestation.
- `POST /v1/integrity/attest` — consume the nonce and perform server-side Play Integrity verification; client verdicts are not trusted.

## Characters and game catalog

- `GET /v1/characters` — list characters owned by the authenticated caller.
- `GET /v1/characters/{character_id}` — return one caller-owned character (IDOR-protected).
- `GET /v1/games` — list the current game catalog for an authenticated caller with `game:read`.
- `GET /v1/games/{game_id}` — return a single game definition.
- `GET /v1/games/{game_id}/access` — return whether the caller has an active entitlement for the game.

## Current catalog / entitlement administration

- `GET /v1/admin/games` — list the current game catalog for an authorized administrator.
- `GET /v1/admin/entitlements` — list entitlements for an authorized administrator.
- `POST /v1/admin/entitlements` — create an entitlement for a user and game.

## Billing and account control

- `GET /v1/billing/plans` — list the canonical product-plan catalog. Price values are display metadata; the browser cannot submit a Stripe price ID.
- `GET /v1/billing/subscriptions` — list subscriptions owned by the authenticated caller.
- `POST /v1/billing/subscriptions` — create a provider-neutral pending subscription intent. The Web UI uses this only for the zero-price plan; paid checkout uses the server-owned route below.
- `POST /v1/billing/checkout-sessions` — create or resume a Stripe-hosted subscription Checkout session for a canonical SENTINEL plan code. Core owns provider selection, Stripe price ID, test/live mode, redirect URLs and subscription metadata. The local subscription remains `PENDING` and grants no paid feature until a verified provider lifecycle event arrives.
- `GET /v1/billing/features` — return feature codes derived server-side from the caller's `ACTIVE` subscriptions only.
- `POST /v1/billing/provider-webhooks/{provider}` — cryptographically verified external-provider ingress. Stripe uses its native `Stripe-Signature` over the exact raw body; the generic signed adapter uses `X-Billing-Signature: t=<unix>,v1=<hmac-sha256>`. Stale, malformed, mode-mismatched or invalid signatures fail closed.
- `POST /v1/billing/webhooks/{provider}` — legacy/internal shared-token ingress. `BillingService` restricts this path to the `manual` and `test` providers; it cannot activate an arbitrary external-provider subscription.

The Stripe adapter maps only bounded subscription lifecycle state into the existing server-authoritative state machine: `active`/`trialing` → `ACTIVE`; `past_due`/`unpaid`/`incomplete`/`paused` → `PAST_DUE`; `canceled` → `CANCELED`; `incomplete_expired` → `EXPIRED`. A signed Stripe subscription event binds the provider subscription ID to the server-created local UUID carried in Stripe metadata; client payloads never assert entitlement state. Snapshot reconciliation uses the same lifecycle path. Terminal `CANCELED` and `EXPIRED` states cannot be reactivated by a later event.

Stripe integration is disabled unless complete environment-injected configuration is present. Test mode is the normal pre-release path. Live mode additionally requires `SENTINEL_ENV=production` and explicit `SENTINEL_STRIPE_ALLOW_LIVE=true`; repository code and CI do not supply live credentials or perform live charges.

## Companion

- `WS /v1/companion/ws` — loopback-only Companion socket. Runtime activation requires a valid opaque Core session in the `Authorization: Bearer ...` header and an ACTIVE subscription-derived `companion` feature. Local peer authentication and protocol/capability negotiation remain additional fail-closed gates.
- `GET /v1/companion/voice/status` — caller-scoped voice capability/limit readback. Requires the existing `game:read` policy plus ACTIVE `companion` feature. Returns availability and bounds only; provider credentials are never exposed.
- `POST /v1/companion/voice/transcribe` — consent-gated bounded WebM/Opus STT plus server-authoritative presentation-intent classification. The response intentionally omits the transcript and can produce only `OBSERVE`, `ACKNOWLEDGE`, `DISMISS` or a fail-closed reason such as `ACTION_GATEWAY_REQUIRED`.
- `POST /v1/companion/voice/synthesize` — consent-gated bounded TTS. Output is validated as bounded WAV bytes and remains a presentation surface, not a gameplay action surface.

The voice routes never grant `game:write`. Raw voice audio/transcripts are not stored in SENTINEL audit metadata. If no voice provider is configured, the routes report provider unavailability instead of silently falling back to a browser speech service. See `docs/COMPANION_VOICE_RUNTIME_V1.md`.

## Operational observability

Every HTTP response carries a normalized `X-Request-ID` and a server-generated `X-Sentinel-Trace-ID`. Route-template/method/status-class operational metrics are bounded and never use request/trace IDs as metric labels.

- `GET /v1/admin/observability` — existing admin-token-protected bounded JSON operational snapshot: counters, local p50/p95/max latency, capacity/overflow evidence and a small recent correlation ring.
- `GET /v1/admin/metrics` — existing admin-token-protected OpenMetrics-compatible plaintext representation of the bounded operational series.

These endpoints are not public metrics surfaces and do not expose a production telemetry-provider credential. The optional PostHog adapter is disabled by default and staging-only; it receives only an allowlisted low-cardinality subset of Companion operational telemetry plus release/environment/source-SHA correlation and no user/device/session/game identity. Provider failure is isolated from Core request serving. See `docs/BLOCK_D_OBSERVABILITY_RESILIENCE_V1.md`.

## World of Warcraft

- `GET /v1/wow/patches` — list known WoW patches.
- `GET /v1/wow/patches/{patch_id}` — return a specific WoW patch.
- `GET /v1/wow/realms` — list known WoW realms.
- `GET /v1/wow/realms/{realm_id}` — return a specific WoW realm.
- `POST /v1/wow/realms/{realm_id}/observations` — accept an administrator-authorized realm observation.
- `GET /v1/devices/me` — return the caller's currently bound device, when present.
- `GET /v1/entitlements/me` — return the caller's game entitlements with game metadata.
- `GET /v1/entitlements/{entitlement_id}` — return one caller-owned game entitlement with game metadata.

## Recommendations

- `POST /v1/recommendations` — non-authoritative recommendation output with confidence, provenance and provider/model identity where applicable. Explicit unknown provider selection fails closed.

`docs/ARCHITECTURE_V4.md` and `docs/SENTINEL_MASTER_ARCHITECTURE_v0.3.md` define architecture targets and must not be treated as runtime route inventories.

## Authentication notes

Bearer access tokens are opaque values. The server stores only SHA-256 digests. Access tokens, refresh tokens, proof signatures, provider secrets and raw private-key material are not returned in logs or audit metadata.
