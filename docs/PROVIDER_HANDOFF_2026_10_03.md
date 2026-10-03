# Provider handoff — 2026-10-03

No credentials are recorded here. Production activation is Owner-gated. Code readiness and console activation are separate evidence classes.

| Provider | Observed control plane | Next external value or gate |
|---|---|---|
| Google | Cloud Auth overview reports Site Unavailable in Work Cloud Browser | Owner access to a staging project; Web OAuth client audience; branding/test audience; stable physical signing SHA-1 from existing custody before Android client |
| Telegram | Existing account requires QR/phone login in Work; no bot recreated | Owner sign-in to existing identity and BotFather Mini App → Bot Settings → Web Login; public OIDC client ID and native secret custody |
| VK ID | Work browser site-safety policy blocked developer portal | Owner ordinary Chrome login; existing/new staging application; return only public numeric application ID |
| Render | Core staging live at baseline e7089ae659cd58a05bdd4621155a9df013daab12 | Automatic main staging deployment and exact-SHA health/browser verification after merge |
| Neon | Existing sentinel-pre-release project, PostgreSQL 18, ready branch main and retained recovery branch | Existing migration/runtime credential separation retained; no new passwords or DB permissions requested |
| Resend | Existing staging sandbox API-key metadata; no domains configured | Native Render key custody; free staging sender plus exact recipient allowlist; owned-domain DNS only when Owner chooses it |
| PostHog | Connected Default project; onboarding and ingestion metadata true | Confirm project ownership/purpose before changing telemetry; no raw events read and no healthy claim for SENTINEL |
| Sentry | No callable connector; read-only script requires native account auth | Owner connection or console sign-in; no DSN/secret supplied in chat |
| Stripe | Reconnected sandbox `acct_1U3douHDnOpHCmiX`, `livemode=false`; existing Core Plus EUR 9.99/month test price verified; staging webhook `we_1UMSMLHDnOpHCmiXP01o0zx4` created | Webhook signing secret transferred directly into Render custody; restricted test API key still required, then exact-candidate checkout/webhook acceptance; no live billing activation |

## Exact auth values

- Core Google audience: `SENTINEL_GOOGLE_WEB_CLIENT_ID` (Web client ID, not Android client ID). `SENTINEL_GOOGLE_AUTH_ENABLED=false` until verified configuration. Android physical package: `com.alpha0.app.physicaltest`; stable SHA-1 only through Owner signing custody. Production package is a separate future slot; no debug signer binding is created.
- Telegram physical callback: `com.alpha0.app.physicaltest.auth://callback`; debug callback: `com.alpha0.app.auth.dev://callback`; production slot: `com.alpha0.app.auth://callback`. Register only callbacks actually accepted by the provider console; a native-scheme acceptance remains unverified. Core `SENTINEL_TELEGRAM_REDIRECT_URIS` must be the exact registered subset. Public `SENTINEL_TELEGRAM_CLIENT_ID`; secret `SENTINEL_TELEGRAM_CLIENT_SECRET` belongs in provider/Render custody. Keep `SENTINEL_TELEGRAM_AUTH_ENABLED=false` until real round trip.
- VK: public decimal `SENTINEL_VK_CLIENT_ID` must match repository build variable, Core environment and Android manifest; exact callback `vk<ID>://vk.ru/blank.html`. Keep `SENTINEL_VK_AUTH_ENABLED=false` until real round trip. No placeholder or mismatched callback can activate discovery.

Telegram official reconciliation: https://core.telegram.org/bots/telegram-login specifies OIDC discovery at https://oauth.telegram.org/.well-known/openid-configuration, authorization code with PKCE S256, registered redirect, ID-token audience/issuer/expiry/nonce verification and no UserInfo endpoint. Existing FEDERATED_AUTH_V1 uses those boundaries; minimal scopes do not request phone or bot messaging authority. Real login/link/MFA/cancel/replay acceptance still needs provider activation plus the physical device.

## Failure gates

Stripe Core accepts restricted `rk_test_` and legacy `sk_test_` server keys through the existing `SENTINEL_STRIPE_SECRET_KEY` slot. Prefer a restricted key with only Checkout Session create and Subscription read permissions required by the implemented adapter; verify effective endpoint permissions with an actual sandbox round trip before enabling it. Publishable keys and wrong-mode credentials are rejected. `rk_live_` remains behind the existing production/allow-live gates. The signing secret is separate and belongs in `SENTINEL_STRIPE_WEBHOOK_SECRET`. The exact staging webhook URL is `https://sentinel-core-staging.onrender.com/v1/billing/provider-webhooks/stripe`; only `customer.subscription.created`, `customer.subscription.updated` and `customer.subscription.deleted` are consumed. Public price slot: `SENTINEL_STRIPE_CORE_PLUS_PRICE_ID=price_1UKCjxHDnOpHCmiXzQg7aFXf`. Keep billing disabled until native credentials and an actual test checkout/webhook are verified. API reference: https://docs.stripe.com/keys.

Console preparation after reconnect: webhook `we_1UMSMLHDnOpHCmiXP01o0zx4` is sandbox-only, API version `2026-08-26.dahlia`, account-bound (not Connect) and subscribes only to the three lifecycle events above. Its secret was passed directly from Stripe creation to the existing Render Core environment with merge semantics, alongside the public price ID. No key/secret was stored in Git, diagnostics or handoff files; no API key was created or billing enable flag changed. An enabled provider endpoint is configuration evidence, not proof of delivery or entitlement activation.

Core tests cover disabled/missing/placeholder public configuration, partial invalid allowlist, callback/client mismatch, provider failure, JWT signature/audience/issuer/expiry/nonce, replay and PKCE, link ownership and MFA. These tests do not prove an external client exists. OAuth secrets, API tokens, signing material and raw production credentials must never enter Git, chat, Drive instructions or diagnostics.
