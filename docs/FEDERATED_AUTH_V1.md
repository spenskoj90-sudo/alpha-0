# SENTINEL Federated Authentication V1

**Status:** IMPLEMENTED, PROVIDER-CONFIGURATION-UNVERIFIED  
**Providers:** Google, Telegram, VK

This contract defines the authentication boundary used by SENTINEL Android and Core. Repository implementation and CI can prove protocol, persistence, replay, account-linking and failure semantics. Provider-console registration, real credentials and end-to-end external login remain Owner/environment evidence until exercised.

## 1. Common identity rule

The provider's verified immutable subject is the external identity key. SENTINEL never treats an email-address match as proof that two accounts are the same person.

- New provider subjects may create provider-only SENTINEL accounts.
- Provider-only accounts may have no email and no local password.
- If a provider returns an email already owned by a local SENTINEL account, federated login returns `ACCOUNT_LINK_REQUIRED`.
- Linking a provider to an existing account requires a device-bound SENTINEL session obtained after device proof plus a freshly verified provider identity. A pre-device login session is insufficient.
- A provider subject already bound to another SENTINEL identity cannot be moved implicitly.
- External access tokens, authorization codes, provider passwords and client secrets are never persisted as SENTINEL account credentials.

`external_identities` is protected by FORCE RLS. Ephemeral OAuth/OIDC challenges are protected by FORCE RLS and stored only as SHA-256 digests.

## 2. Google

Android uses AndroidX Credential Manager and the Google ID library. The app first asks Core for a short-lived nonce and the configured Web client ID, then requests a Google ID token through Credential Manager.

Core validates the token before creating or linking any SENTINEL identity:

- RS256 signature against Google's HTTPS JWKS;
- issuer;
- audience / authorized-party semantics;
- expiration and issued-at bounds;
- exact server-issued nonce;
- non-empty provider `sub`.

The Google Web client ID is public configuration and may be returned to Android. No Google client secret is required in the APK.

Google-reported email is metadata, never the provider identity key. SENTINEL promotes Google email verification only when Google's documented authoritative-email conditions are met; otherwise email remains unverified locally.

Required external configuration:

```text
SENTINEL_GOOGLE_AUTH_ENABLED=true
SENTINEL_GOOGLE_WEB_CLIENT_ID=<Google Web OAuth client ID>
```

## 3. Telegram

Telegram uses its documented OpenID Connect Authorization Code flow with PKCE.

Core generates the OAuth state. Android receives the state and PKCE verifier only after Core has persisted the state's SHA-256 digest. The authorization request uses:

- `https://oauth.telegram.org/auth`;
- `response_type=code`;
- `scope=openid profile`;
- PKCE S256;
- state;
- a nonce bound to the same server challenge.

Core exchanges the code server-side at `https://oauth.telegram.org/token` using HTTP Basic client authentication, then validates the returned ID token against Telegram JWKS, issuer, audience, expiration, issued-at and nonce.

The current SENTINEL verifier intentionally accepts Telegram's default RS256 configuration. Changing the BotFather signing algorithm requires a corresponding reviewed verifier change; the server does not silently accept arbitrary algorithms.

Required external configuration:

```text
SENTINEL_TELEGRAM_AUTH_ENABLED=true
SENTINEL_TELEGRAM_CLIENT_ID=<BotFather OIDC client ID>
SENTINEL_TELEGRAM_CLIENT_SECRET=<Owner-managed secret>
SENTINEL_TELEGRAM_REDIRECT_URIS=com.alpha0.app.auth://callback,com.alpha0.app.physicaltest.auth://callback
```

## 4. VK

VK uses Authorization Code + PKCE. The Core adapter follows the current VK ID Android network contract:

- authorization host: `id.vk.ru`;
- token endpoint: `https://id.vk.ru/oauth2/auth`;
- user endpoint: `https://id.vk.ru/oauth2/user_info`;
- `grant_type=authorization_code`;
- exact `code_verifier`, `client_id`, `device_id`, `redirect_uri` and state.

Provider tokens remain inside the Core exchange and are not returned to Android. Provider subject, not email, owns the binding.

Required external configuration:

```text
SENTINEL_VK_AUTH_ENABLED=true
SENTINEL_VK_CLIENT_ID=<VK ID application ID>
SENTINEL_VK_REDIRECT_URIS=vk<VK_CLIENT_ID>://vk.ru/blank.html
```

## 5. Redirect and callback boundary

Browser providers are not allowed to choose an arbitrary redirect target. Android submits the callback URI compiled for its build. Core enables the provider only when at least one redirect URI is configured and accepts a submitted URI only when it exactly matches the provider-specific server allowlist.

Canonical Android callback schemes are separated by distribution identity:

- debug/development: `com.alpha0.app.auth.dev://callback`;
- physical-test diagnostic APK: `com.alpha0.app.physicaltest.auth://callback`;
- release: `com.alpha0.app.auth://callback`.

Telegram uses the SENTINEL callback schemes above when the provider configuration accepts them. VK mobile authorization uses the provider-mandated callback `vk<clientId>://vk.ru/blank.html`. The public VK client ID is compiled into the Android manifest to register that exact scheme; no VK client secret is compiled into the APK. An APK hides the VK option unless Core's declared client ID matches the callback identity compiled into that build.

The Android manifest accepts only the build's compiled scheme plus host `callback`. MainActivity validates both again before forwarding a callback to the auth coordinator.

The PKCE verifier, provider and state survive the browser round trip only inside AES-GCM ciphertext protected by an Android Keystore key. The entry expires after ten minutes and is consumed before provider completion. The callback state is compared in constant time. Core independently enforces its own five-minute one-time challenge.

## 6. Disabled/default behavior

All federated providers are disabled by default. Missing or partial provider configuration never falls back to accepting unverified client claims.

The Android UI is driven by `GET /v1/auth/providers` and shows only providers that Core reports as enabled. Provider secrets are never included in this catalog.

## 7. External acceptance still required

Repository completion does not claim:

- Google Cloud OAuth consent/client registration;
- BotFather OIDC configuration or Telegram Client Secret custody;
- VK ID application registration;
- acceptance of every callback URI by each provider console;
- real-account provider login on a physical device;
- production provider credentials;
- production deployment or release publication.

Those are Owner/environment gates and must be recorded against the exact selected release candidate.
