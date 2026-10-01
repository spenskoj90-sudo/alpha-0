# SENTINEL Provider Status Matrix

**Status:** ACTIVE  
**Reconciled:** 2026-10-01
**Rule:** integration code, deterministic tests, staging network evidence, physical evidence and production activation are separate claims. No cell may be promoted by inference from another column.

The status vocabulary follows the repository product-truth model: `IMPLEMENTED`, `TESTED`, `STAGING-VERIFIED`, `PHYSICAL-VERIFIED`, `ENVIRONMENT-UNVERIFIED`, `MISSING`, `SUPERSEDED`, `HISTORICAL`, `OWNER-GATED`.

| Provider / boundary | CODE | TEST | STAGING | CREDENTIALS | NETWORK | PHYSICAL | PRODUCTION |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stripe Billing | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| Transactional email (Resend / Brevo HTTPS) | IMPLEMENTED | TESTED | STAGING-VERIFIED | STAGING-VERIFIED | STAGING-VERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| Sentry Android | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | HISTORICAL | HISTORICAL | OWNER-GATED |
| PostHog operational telemetry | IMPLEMENTED | TESTED | STAGING-VERIFIED | STAGING-VERIFIED | STAGING-VERIFIED | ENVIRONMENT-UNVERIFIED | MISSING |
| Google federated auth | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| Telegram federated auth | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| VK federated auth | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| STT provider boundary | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| TTS provider boundary | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |

## Exact interpretation

### Stripe

Core owns plan-to-price mapping, checkout-session creation, native `Stripe-Signature` verification, metadata binding, replay-safe lifecycle reconciliation and entitlement authority. CI proves fail-closed/test-mode behavior without live credentials or live charges. The connected sandbox now contains a non-live `SENTINEL Core Plus` product and EUR 9.99/month test price, but Core checkout is still environment-unverified until staging test credentials/webhook configuration are injected and an exact-candidate checkout is exercised. No live payment acceptance is claimed.

### Transactional email

The provider-neutral mail boundary, deterministic test transport and two bounded staging-only HTTPS adapters are implemented: Resend and Brevo. Exactly one provider may be enabled at a time; conflicting provider activation fails closed. This deliberately avoids SMTP because Render Free blocks outbound ports 25/465/587. Public registration/recovery requests remain non-enumerating, while authenticated account-security verification fails closed with explicit provider-unavailable state instead of claiming delivery.

Resend is configured and network-verified for the free staging sandbox. A sending-only key stays in Render Core secret custody; `onboarding@resend.dev` is restricted by an explicit recipient allowlist. Brevo remains disabled. On 2026-10-01, deployed source `25bb96ca926ae53efd20f253d755c9ac178ef264` completed the real Web recovery path with the approved Resend simulator: neutral request, delivered reset email, one-time code consumption, rejected reuse, login using the new password with HttpOnly cookies, and server-confirmed logout/revocation. This test affected only the disposable simulator account. The 2026-09-30 neutral Owner-mailbox delivery is separate transport evidence, not Owner account acceptance.

Arbitrary real recipients still require an owned, verified sending domain. The Owner has deferred that purchase until before release. Transition through sender/domain/API-key configuration; do not rewrite auth flows or expose keys in documentation. `STAGING-VERIFIED` describes the dated sandbox observations, not physical, production or acceptance of a later frozen release candidate.

### Sentry

Android release telemetry is fail-closed unless DSN, exact source SHA and an allowlisted runtime environment are supplied. CI verifies release correlation and privacy scrubbing. A 2026-09-06 physical Android smoke proved the transport at that time only, so network/physical evidence is `HISTORICAL`, not current-candidate acceptance. The Physical Test APK intentionally disables remote telemetry.

### PostHog

The staging-only low-cardinality non-person sink is implemented, deterministic and destination-pinned. The actual Sentinel organization and EU project `245803` were verified before activation. Core is configured through Render secret custody, with person profiling disabled and no browser SDK or replay enabled by this integration. PostHog contains the actual `core.runtime.started` event for deployed source `25bb96ca926ae53efd20f253d755c9ac178ef264`, environment `staging`, release `1.0.0-rc2`, timestamp `2026-10-01T06:25:49.493Z`. Earlier ingestion on `88961e844a2f8f96912bbc7ddfea19a0c99a57f4` is separate dated evidence. This verifies Core lifecycle delivery, not Companion host or user activity. Production delivery is `MISSING` **by design** under the current contract: the runtime rejects production PostHog activation rather than silently broadening telemetry authority. Provider-side retention and alert provisioning are not inferred from ingestion.

### Google / Telegram / VK

Provider discovery, challenge/state/nonce handling, PKCE where applicable, provider-token verification, FORCE-RLS challenge persistence, explicit account linking and Android callback isolation are implemented and tested. Google Credential Manager and Telegram OIDC/PKCE were rechecked against current September 2026 provider guidance; no protocol rewrite is currently required. Android physical/release artifact generation now binds the public VK application identity and exact callback URI into compiled-artifact evidence rather than relying on an implicit build default. Real provider-console application registration, credentials, network login and physical-device provider acceptance remain environment/Owner gates.

### STT / TTS

The voice runtime has provider-neutral HTTPS contracts, bounded payloads, explicit consent, short-lived microphone lease, presentation-only classification, action-like speech fail-closed behavior and fixed-text TTS authority. No production vendor is selected/accepted here. Provider credentials/network behavior and real microphone/acoustic acceptance remain Owner/environment gates.

## Zero-cost testing posture

Pre-release testing does not require paid provider plans. The active strategy is documented in `docs/FREE_TESTING_INFRASTRUCTURE_STRATEGY.md`.

- Stripe acceptance uses sandbox/test mode; live charges remain Owner-gated.
- Resend Free is active through the restricted sandbox sender and sending-only staging key; an owned sending domain is deferred until before release. Brevo Free remains an HTTPS fallback when a verified sender/API key is available.
- Sentry free/developer monitoring is optional; Physical Test remains local-forensic by design.
- Federated auth uses provider development/test registrations before production credentials.
- Free hosting/database alternatives are evaluated as testing dependencies only; they are not promoted into production merely because they cost zero.

## Release rule

A provider may be promoted to `STAGING-VERIFIED`, `PHYSICAL-VERIFIED` or production acceptance only with evidence bound to the exact candidate being accepted. Historical provider smoke, repository tests or configuration presence cannot substitute for that evidence.
