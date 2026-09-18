# SENTINEL Android Product Shell v1

**Status:** ACTIVE  
**Purpose:** define the minimum user-facing Android product that must exist before another physical product test is requested.

## Product boundary

An installable APK, successful authentication, device proof and green CI are necessary but are not sufficient product-readiness evidence. The Android application must expose a coherent user journey before and after authentication.

## Required pre-authentication surface

Every build exposes a persistent top app bar and overflow menu before sign-in. The menu provides:

- Settings;
- Updates;
- Help;
- About.

Settings persist locally and do not require an account. Language choices are System, Russian and English. Appearance choices are System, Light and Dark. A language or theme change applies immediately and survives process restart.

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
- both light and dark color schemes compile;
- authenticated primary routes exist;
- onboarding is scrollable and the card decoration uses `matchParentSize`, not `fillMaxSize` measurement;
- Update Center is backed by Play In-App Updates libraries;
- `versionCode` is positive and monotonically advanced for each installable distribution;
- API 35 instrumentation and JVM tests pass on the exact SHA.

Physical acceptance remains required for the exact selected artifact. CI does not manufacture a physical PASS.
