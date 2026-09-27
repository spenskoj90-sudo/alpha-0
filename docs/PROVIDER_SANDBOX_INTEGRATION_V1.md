# SENTINEL Provider Sandbox Integration V1

Status: **ACTIVE PRE-RELEASE CONTRACT**

This document defines the provider and database-runtime boundaries implemented for the pre-release environment. It is deliberately narrower than production activation: repository code may prove protocol semantics, test-mode provider behavior and fail-closed configuration without creating live charges, sending production email, enabling production telemetry or deploying production traffic.

## 1. PostgreSQL / PgBouncer service-role boundary

SENTINEL keeps PostgreSQL `FORCE ROW LEVEL SECURITY` and the existing `app.service_role=true` service policy. The application no longer sends `app.service_role` as a PostgreSQL startup parameter.

Every SQLAlchemy transaction begins with:

```sql
SELECT set_config('app.service_role', 'true', true)
```

The third argument is `true`, so the setting is transaction-local and PostgreSQL clears it automatically at commit/rollback. This is compatible with transaction-pooling endpoints such as Neon PgBouncer and prevents a session-scoped privilege bit from leaking to another pooled client.

The same rule applies to:

- `PostgresStore`;
- `UserAccountStore`;
- the durable event worker runtime;
- runtime-retention maintenance;
- the migration runner.

Migrations remain checksum-verified and execute inside explicit transactions. No migration weakens FORCE RLS or bypasses the service policy.

## 2. Stripe pre-release billing

Stripe is an optional `BillingProviderAdapter` implementation. It is disabled unless complete environment configuration is supplied.

### Checkout

Paid Web plans use server-created Stripe-hosted Checkout sessions. The browser may submit only a canonical SENTINEL `plan_code`. Core owns:

- Stripe provider selection;
- Stripe price ID mapping;
- test/live mode;
- success/cancel URLs;
- local subscription identity;
- Stripe metadata binding;
- idempotency key.

Core first creates (or reuses) a local `PENDING` Stripe subscription. `PENDING` never grants paid features. Retry/cancel paths reuse the same local subscription UUID and Stripe idempotency key instead of trusting browser-supplied provider identifiers.

### Webhook verification

Stripe lifecycle ingress uses the native `Stripe-Signature` header and verifies HMAC-SHA256 over the exact raw request body plus Stripe timestamp. Verification rejects:

- body tampering;
- missing/malformed signatures;
- stale timestamps;
- test/live mode mismatch;
- malformed provider objects;
- unsupported subscription state.

Only these Stripe subscription event types enter the lifecycle boundary:

- `customer.subscription.created`;
- `customer.subscription.updated`;
- `customer.subscription.deleted`.

Other correctly signed Stripe events are explicitly ignored rather than interpreted as subscription authority.

The local subscription UUID is carried in server-created Stripe metadata. A signed subscription event may bind the durable Stripe `sub_...` identifier to that UUID once. The browser cannot provide this binding.

### Lifecycle mapping

| Stripe status | SENTINEL state | Paid feature grant |
| --- | --- | --- |
| `active`, `trialing` | `ACTIVE` | yes, according to plan |
| `past_due`, `unpaid`, `incomplete`, `paused` | `PAST_DUE` | no |
| `canceled` | `CANCELED` | no |
| `incomplete_expired` | `EXPIRED` | no |

`PENDING`, `PAST_DUE`, `CANCELED` and `EXPIRED` never grant paid features. Terminal SENTINEL states remain terminal. Snapshot reconciliation maps provider state through the same state machine and uses a deterministic provider-revision event ID for replay safety.

### Current Stripe sandbox inventory · 2026-09-27

The connected Stripe account is a **test/sandbox** account. The following non-live catalog objects now exist for pre-release acceptance:

- product: `prod_VKsUERZXQrdT93` — **SENTINEL Core Plus**;
- recurring price: `price_1UKCjxHDnOpHCmiXzQg7aFXf`;
- amount: EUR 9.99 / month;
- lookup key: `sentinel_core_plus_monthly_test`;
- both objects report `livemode=false`.

This proves catalog preparation only. Core checkout remains intentionally disabled until the **test-mode** Stripe secret key, webhook signing secret, success/cancel URLs and price ID are injected through the staging secret channel. None of those secrets belong in Git, documentation, chat or Android assets.

### Live-mode gate

Normal pre-release configuration is Stripe test mode. Live mode additionally requires all of:

- `SENTINEL_STRIPE_ENABLED=true`;
- `SENTINEL_STRIPE_LIVEMODE=true`;
- `SENTINEL_ENV=production`;
- `SENTINEL_STRIPE_ALLOW_LIVE=true`;
- externally injected live credentials and price mapping.

Repository CI does not supply these values. This implementation does not perform a live charge and does not activate production billing.

## 3. PostHog staging telemetry

The PostHog adapter is optional and **disabled by default**. Activation is accepted only for `SENTINEL_ENV=staging` and requires an externally injected project key plus exact release/source identity.

Provider payloads contain only:

- Companion operational event name;
- timestamp;
- constant non-person distinct ID `sentinel-runtime`;
- `$process_person_profile=false`;
- environment;
- release;
- exact 40-character source SHA;
- a fixed allowlist of low-cardinality operational attributes.

The adapter drops user/device/session/game/request identity fields even if a local event carries them. It does not send raw payloads, transcripts, audio, email addresses, access/refresh tokens or game state.

PostHog delivery is fail-isolated: provider failure increments a bounded local dropped counter and does not fail the Core request or Companion runtime path. Local/PostgreSQL telemetry remains the canonical operational plane.

This repository contract does not claim production PostHog activation, account-side retention configuration or production alert thresholds.

## 4. Transactional email boundary

Email delivery has a provider-neutral bounded transport contract:

- `DisabledEmailTransport` is the default and fails closed;
- `TestEmailTransport` is deterministic, bounded and network-free;
- `ResendEmailTransport` is an HTTPS adapter with bounded request/response handling;
- `BrevoEmailTransport` is a second bounded HTTPS adapter pinned to `https://api.brevo.com/v3/smtp/email`;
- exactly one external provider may be enabled at a time; ambiguous multi-provider activation fails closed;
- external activation is staging-only and requires an injected provider API key plus a provider-accepted sender identity.

Recipient, subject and plain-text body are validated and bounded. Provider credentials are excluded from object representations and repository state. The Brevo path deliberately uses HTTPS instead of SMTP so staging does not depend on outbound SMTP ports.

Account registration/email-verification and password-recovery flows use this shared boundary. Requests remain non-enumerating, raw one-time credentials are never persisted, and provider delivery failure does not roll back account creation or reveal whether an email is registered. Real external delivery still requires one staging provider to be configured and exercised; production email-provider activation remains an external Owner gate.

## 5. Federated authentication boundary

Google, Telegram and VK authentication are disabled by default and become visible to Android only when Core reports a complete provider configuration.

- Google uses Android Credential Manager with a Core-issued one-time nonce. Core validates the Google ID token signature, issuer, audience, time bounds, nonce and provider subject.
- Telegram uses Authorization Code + PKCE against `oauth.telegram.org`; the client secret exists only on Core, and the resulting RS256 ID token is verified server-side.
- VK uses the current `id.vk.ru` Authorization Code + PKCE contract. Android registers the canonical `vk<clientId>://vk.ru/blank.html` callback using the public application ID; no VK client secret is embedded in the APK.
- Telegram/VK redirect targets must match provider-specific server allowlists exactly. Core stores only the SHA-256 digest of the one-time state and its bounded redirect context under FORCE RLS.
- Android encrypts pending provider/state/PKCE verifier data with AES-GCM under Android Keystore and consumes it on callback.
- Existing accounts are never auto-linked from an email collision. Linking requires a valid SENTINEL Bearer session and a new verified provider proof.

### Current provider-console activation checklist · 2026-09-27

Repository implementation was reconciled against current provider guidance without enabling any external credential:

- **Google:** Android uses Credential Manager and the current Google ID library line. Provider setup needs a Google Auth Platform project plus the Web OAuth client ID used as the server client ID; Android distribution identity additionally binds package name and signing-certificate fingerprint. The ID token is still validated by Core. Current official Android guidance: https://developer.android.com/identity/sign-in/credential-manager-siwg
- **Telegram:** the implemented Authorization Code + PKCE flow matches Telegram's current OIDC login contract. BotFather supplies the Login client ID/secret and Allowed URLs; Core validates the returned ID token against Telegram JWKS. Current official contract: https://core.telegram.org/bots/telegram-login
- **VK ID:** the existing PKCE/provider-specific redirect implementation remains fail-closed and environment-unverified. Physical-test CI consumes the non-secret GitHub Actions variable `SENTINEL_VK_CLIENT_ID` (default `0` while VK is disabled); the stable physical-test-update and release-candidate workflows also accept an explicit public `vk_client_id` input and verify the compiled `vk<id>://vk.ru/blank.html` identity. Production or staging promotion still requires provider-console registration and exact real-account callback evidence.

External provider credentials remain Owner-managed. The client never enables a provider simply because code exists; Core discovery must report a complete configuration first.

Provider-console setup and real-account external login are environment evidence, not repository claims. See `docs/FEDERATED_AUTH_V1.md`.

## 6. Explicit non-claims

This implementation does **not** claim or perform:

- production deployment or production traffic;
- Stripe live-mode objects or live charges (the current product/price inventory is sandbox-only);
- production payment credentials;
- production PostHog ingestion, retention or alert provisioning;
- a real external email-provider delivery to a user;
- production email-provider credentials;
- release signing, version tagging or publication;
- physical-device acceptance.

Those remain external/final-stage gates. Repository CI and staging evidence may prove only the exact behavior they actually execute.
