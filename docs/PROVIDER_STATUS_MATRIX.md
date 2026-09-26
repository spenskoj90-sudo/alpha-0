# SENTINEL Provider Status Matrix

**Status:** ACTIVE  
**Reconciled:** 2026-09-25  
**Rule:** integration code, deterministic tests, staging network evidence, physical evidence and production activation are separate claims. No cell may be promoted by inference from another column.

The status vocabulary follows the repository product-truth model: `IMPLEMENTED`, `TESTED`, `STAGING-VERIFIED`, `PHYSICAL-VERIFIED`, `ENVIRONMENT-UNVERIFIED`, `MISSING`, `SUPERSEDED`, `HISTORICAL`, `OWNER-GATED`.

| Provider / boundary | CODE | TEST | STAGING | CREDENTIALS | NETWORK | PHYSICAL | PRODUCTION |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stripe Billing | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| Resend email | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| Sentry Android | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | HISTORICAL | HISTORICAL | OWNER-GATED |
| PostHog operational telemetry | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | MISSING |
| Google federated auth | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| Telegram federated auth | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| VK federated auth | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| STT provider boundary | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |
| TTS provider boundary | IMPLEMENTED | TESTED | ENVIRONMENT-UNVERIFIED | OWNER-GATED | ENVIRONMENT-UNVERIFIED | ENVIRONMENT-UNVERIFIED | OWNER-GATED |

## Exact interpretation

### Stripe

Core owns plan-to-price mapping, checkout-session creation, native `Stripe-Signature` verification, metadata binding, replay-safe lifecycle reconciliation and entitlement authority. CI proves fail-closed/test-mode behavior without live credentials or live charges. No current exact-candidate external Stripe network/payment acceptance is claimed.

### Resend

The provider-neutral mail boundary, deterministic test transport and bounded staging-only Resend adapter are implemented. Public registration/recovery requests remain non-enumerating, while the authenticated account-security verification path now fails closed with explicit provider-unavailable state instead of claiming delivery. Real current-candidate Resend delivery remains environment-unverified; production credentials and activation remain Owner-gated.

### Sentry

Android release telemetry is fail-closed unless DSN, exact source SHA and an allowlisted runtime environment are supplied. CI verifies release correlation and privacy scrubbing. A 2026-09-06 physical Android smoke proved the transport at that time only, so network/physical evidence is `HISTORICAL`, not current-candidate acceptance. The Physical Test APK intentionally disables remote telemetry.

### PostHog

The staging-only low-cardinality non-person sink is implemented, deterministic and destination-pinned. Actual staging account/network ingestion is not currently claimed. Production delivery is `MISSING` **by design** under the current contract: the runtime rejects production PostHog activation rather than silently broadening telemetry authority.

### Google / Telegram / VK

Provider discovery, challenge/state/nonce handling, PKCE where applicable, provider-token verification, FORCE-RLS challenge persistence, explicit account linking and Android callback isolation are implemented and tested. Real provider-console application registration, credentials, network login and physical-device provider acceptance remain environment/Owner gates.

### STT / TTS

The voice runtime has provider-neutral HTTPS contracts, bounded payloads, explicit consent, short-lived microphone lease, presentation-only classification, action-like speech fail-closed behavior and fixed-text TTS authority. No production vendor is selected/accepted here. Provider credentials/network behavior and real microphone/acoustic acceptance remain Owner/environment gates.

## Release rule

A provider may be promoted to `STAGING-VERIFIED`, `PHYSICAL-VERIFIED` or production acceptance only with evidence bound to the exact candidate being accepted. Historical provider smoke, repository tests or configuration presence cannot substitute for that evidence.
