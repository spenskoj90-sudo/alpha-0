# SENTINEL free testing infrastructure strategy

**Status:** ACTIVE FOR PRE-RELEASE TESTING  
**Verified:** 2026-09-27  
**Production rule:** free-tier constraints may be accepted for development/staging evidence, but may not be silently promoted into production SLOs.

The Human Owner has chosen to defer paid infrastructure until the product is close to public release. This document separates the **zero-cost testing stack** from the later **production-optimized stack** so repository work does not accidentally depend on a paid service.

## Decision matrix

| Boundary | Zero-cost testing path | Current decision | Production transition |
| --- | --- | --- | --- |
| Core API | Render Free + Android readiness preflight + replay-safe alternate ingress reads | **KEEP** | move to always-on compute or another production host after release acceptance |
| Web Control Plane | Render Free | **KEEP** | choose production CDN/server runtime after final Web acceptance |
| Independent edge ingress | Cloudflare Workers Free is suitable for a lightweight relay/health edge, not the Python Core | **PREPARE, DO NOT REQUIRE** | production DNS/WAF/edge provider selected at release stage |
| PostgreSQL | existing Neon managed PostgreSQL; optional isolated recovery targets | **KEEP NEON; DO NOT MIGRATE WITHOUT NEED** | managed production PostgreSQL with backups/availability evidence |
| Email | Resend Free with a bounded test sender/recipient allowlist; Brevo Free HTTPS fallback | **USE FREE SANDBOX NOW** | owned sending domain before release; replace sender/key through configuration |
| Error monitoring | Sentry Developer/Free where a DSN is configured | **OPTIONAL TEST OBSERVABILITY** | production plan selected from measured event volume |
| Billing | Stripe test/sandbox mode | **USE FOR ACCEPTANCE WITHOUT LIVE MONEY** | live mode only after Owner authorization |
| Federated auth | provider development/test apps | **USE FREE PROVIDER SANDBOX/DEV CONFIG** | production registrations/redirects at release stage |
| Design laboratory | Lovable Free workspace | **KEEP AS REFERENCE LAB** | production remains native in alpha-0 |

## Why Core stays on Render Free for now

The current physical evidence shows the cost of Render Free cold start, and Android now mitigates it with a replay-safe `GET /healthz` readiness path before authentication writes.

Migrating only to obtain another free compute instance is not automatically an improvement. As of this verification:

- Render Free spins down after 15 minutes without inbound traffic and provides 750 free instance-hours per workspace per month.
- Koyeb offers one 512 MB / 0.1 vCPU Free Instance, but it also scales to zero after one hour without traffic.
- Therefore Koyeb may reduce the *frequency* of cold starts but does not remove the cold-start class, while adding another deployment/security/secret surface.

**Decision:** keep Render Free during testing. Reconsider only if exact physical evidence after the readiness preflight still shows an unacceptable failure rate.

Official references:
- https://render.com/docs/free
- https://www.koyeb.com/docs/reference/instances

## Independent edge option

Cloudflare Workers Free currently provides up to 100,000 requests/day with a 10 ms CPU-time limit per invocation. That is useful for a narrow HTTP relay, health probe, static routing policy or provider-independent ingress endpoint. It is **not** a suitable host for the existing FastAPI Core without an architectural rewrite.

The repository should keep the alternate-ingress contract provider-neutral so a Cloudflare Worker, Vercel edge route or another edge provider can be inserted without changing Android auth semantics.

Official references:
- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/workers/platform/limits/

## Database testing

Do not move the authoritative database merely because a second provider is free.

Neon is the managed PostgreSQL authority for SENTINEL staging. Its database identity, live migration checksums and runtime connectivity must be verified independently of CI's disposable PostgreSQL integration database. An alternative free service is only an isolated recovery target, not an authority migration.

Supabase Free currently includes two free projects, 500 MB database size per project, 5 GB egress, 50,000 MAU and 500,000 Edge Function invocations; inactive free projects may pause after one week. This is adequate for:

- migration dry-runs;
- RLS verification;
- disaster-recovery rehearsal;
- isolated integration tests.

It is not, by itself, production availability evidence.

Official references:
- https://supabase.com/docs/guides/platform/billing-on-supabase
- https://supabase.com/pricing

## Email testing

Resend Free currently includes 3,000 transactional emails/month and 100/day. The Owner has chosen free testing now and an owned domain before release. Use `onboarding@resend.dev` with a sending-only staging key and an explicit `SENTINEL_RESEND_ALLOWED_RECIPIENTS` list. This sender supports documented provider simulators and the provider account's own mailbox; it does not support arbitrary real recipients without an owned, verified domain. Secret custody and current runtime proof belong in provider-native configuration and exact-candidate evidence, not this strategy document.

Brevo Free is now a repository-supported HTTPS fallback. Its current Free plan includes 300 email sends/day and supports transactional email. SENTINEL uses Brevo's `POST https://api.brevo.com/v3/smtp/email` HTTP API rather than SMTP because Render Free blocks outbound SMTP ports 25, 465 and 587. The Brevo adapter pins the official HTTPS endpoint, bounds responses and remains staging-only/fail-closed.

Exactly one external email provider may be enabled at a time. A real mailbox delivery test still requires provider-accepted sender/recipient identities. For later owned-domain staging acceptance, verify `mail.<owned-domain>` and replace the sender/API key through environment configuration; the shared transport and auth flows do not change. See `PROVIDER_SANDBOX_INTEGRATION_V1.md` for limits, migration and the separate production activation gate.

Resend test addresses such as `delivered@resend.dev`, `bounced@resend.dev` and `complained@resend.dev` may be used for provider integration tests without affecting domain reputation. Brevo also provides an API sandbox mode that validates requests without sending. Neither substitutes for real mailbox verification acceptance.

Official references:
- https://resend.com/pricing
- https://resend.com/changelog/three-domains-on-the-free-tier
- https://resend.com/changelog/sending-test-emails

## Observability

SENTINEL keeps remote telemetry fail-closed. Local forensic diagnostics remain the acceptance authority for Physical Test builds.

Sentry's free Developer tier can be used for staging/release-candidate error monitoring after an Owner-managed DSN exists. It is optional during physical testing and must not cause a release build to fail when unavailable.

Official reference:
- https://sentry.io/solutions/ai-observability/

## Billing

Stripe sandbox/test mode is the correct no-cost acceptance path. Test products, prices, checkout, signatures and lifecycle reconciliation can be exercised without live charges.

Live-mode keys, real charges and production webhook activation remain release-stage Owner gates.

## Promotion rule

A free testing service is promoted into the release architecture only when all of the following are true:

1. exact-candidate network evidence is successful;
2. limits cover the expected launch load with margin;
3. backup/recovery and failure behavior are accepted;
4. secrets can be injected through the production secret channel;
5. the Owner approves any paid plan or live-account change;
6. migration backout is documented.

Until then, free providers are **testing dependencies**, not product authority.
