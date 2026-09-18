# SENTINEL Android Product Shell v1

**Status:** ACTIVE  
**Purpose:** define the minimum user-facing Android product that must exist before another physical product test is requested.

## Product boundary

An installable APK, successful authentication, device proof and green CI are necessary but are not sufficient product-readiness evidence. The Android application must expose a coherent user journey before and after authentication.

## Product identity and distribution

The installed application must use a SENTINEL-owned launcher icon rather than an Android/template fallback. The icon is part of the product contract and is referenced explicitly from the application manifest.

Ordinary users and invited testers use the same release application ID and signing lineage. Access is separated by Google Play tracks (Internal/Closed testing before wider release), not by embedding tester or owner privilege in a different APK. The dedicated `physicalTest` build is an isolated diagnostic instrument with the `.physicaltest` application-ID suffix, a distinct label and forensic diagnostics.

Owner/admin authority is never derived from the Android package variant. Privilege remains server-authoritative and must be protected independently by strong authentication/MFA.

## Required pre-authentication surface

Every build exposes a persistent top app bar and overflow menu before sign-in. The menu provides:

- Settings;
- Updates;
- Help;
- About.

Settings persist locally and do not require an account. Language choices are System, Russian and English. Appearance choices are System, Light and Dark. A language or theme change applies immediately and survives process restart. The authentication surface is scroll-safe and includes a non-enumerating password-recovery flow plus post-registration email verification with resend and verify-later paths. When Core reports configured providers, the same surface offers Google Credential Manager and Telegram/VK PKCE sign-in. Security shows caller-scoped account-access state and supports explicit provider linking; email equality alone never links identities.

## Required authenticated shell

After device proof the application exposes four stable primary destinations:

1. Home — live device and entitlement summary, support entry point and sign-out.
2. Games — server-authoritative game entitlements and details.
3. Security — device state, key rotation and device revocation.
4. Activity — bounded local session/device/diagnostic state without inventing server events.

Secondary routes include game details and the quality report. Every route remains reachable with large font scaling; decorative rendering must not affect layout measurement.

## Device onboarding

Device setup is a scrollable three-step flow:

1. show the hardware-backed public identity status;
2. explain the optional background-operation setting;
3. connect and prove the device.

The primary action must remain visible/reachable on the minimum supported display and with enlarged text. Only the public key/fingerprint crosses the Core boundary; the private key remains non-exportable in Android Keystore.

## Update model

The application contains an Update Center using Google Play In-App Updates. The preferred test and release channel is Google Play Internal Testing followed by the appropriate release track. This gives stable app signing, monotonic `versionCode`, Play-distributed replacement installation and user-confirmed flexible/immediate update flows.

Sideloaded physical-test APKs remain diagnostic instruments. Android may require Package Installer confirmation and Play Protect evaluation. The application must never disable, bypass or misrepresent those platform protections.

The repository can implement and test the update client, version monotonicity and signing/publication workflow boundaries. Actual Play Console application creation, tester enrollment, signing-key custody, Play service-account credentials and track publication remain Owner actions.

## Acceptance

Routine Android acceptance must prove at least:

- pre-auth menu routes exist;
- all language/theme choices exist and preferences persist;
- sign-in exposes password recovery and registration exposes email verification without trapping a user when external mail delivery is unavailable;
- federated provider buttons are server-driven and hidden when a provider or this APK's callback identity is not configured;
- Google uses Credential Manager with a Core-issued nonce; Telegram/VK browser PKCE state survives Activity recreation under Android Keystore protection;
- Security can explicitly link an additional provider using the current SENTINEL session plus fresh provider proof;
- both light and dark color schemes compile;
- authenticated primary routes exist;
- onboarding is scrollable and the card decoration uses `matchParentSize`, not `fillMaxSize` measurement;
- Update Center is backed by Play In-App Updates libraries;
- the manifest names the SENTINEL launcher icon and product-shell tests lock its branded palette;
- release uses the Play distribution channel while the isolated physical-test package reports the diagnostic channel;
- `versionCode` is positive and monotonically advanced for each installable distribution;
- API 35 instrumentation and JVM tests pass on the exact SHA.

Physical acceptance remains required for the exact selected artifact. CI does not manufacture a physical PASS.
