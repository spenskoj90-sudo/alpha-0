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

## 4. Resend email boundary

Email delivery now has a provider-neutral bounded transport contract:

- `DisabledEmailTransport` is the default and fails closed;
- `TestEmailTransport` is deterministic, bounded and network-free;
- `ResendEmailTransport` is an HTTPS adapter with bounded request/response handling;
- Resend activation is staging-only and requires externally injected API key and verified sender address configuration.

Recipient, subject and plain-text body are validated and bounded. Provider credentials are excluded from object representations and repository state.

No product flow automatically sends email in this block. A real message requires a separately defined product event, intended recipient and staging credential. This prevents provider availability from being mistaken for an authorization to send mail.

## 5. Explicit non-claims

This implementation does **not** claim or perform:

- production deployment or production traffic;
- Stripe live-mode objects or live charges;
- production payment credentials;
- production PostHog ingestion, retention or alert provisioning;
- a real Resend delivery to a user;
- production Resend credentials;
- release signing, version tagging or publication;
- physical-device acceptance.

Those remain external/final-stage gates. Repository CI and staging evidence may prove only the exact behavior they actually execute.
