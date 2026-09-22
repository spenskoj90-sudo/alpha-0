# Android physical-test update channel

## Problem confirmed on 2026-09-21

Two consecutive physical-test APKs used the same application ID but different ephemeral Android debug certificates. Android therefore rejected an in-place update as an incompatible package.

Observed signer certificate SHA-256 values:

- fc92a17c…: 3663c6c039941d5340dcd885c8f01cca6d499066bc3dfbee67e90f9fcb368a6a
- bbbd3f0f…: 550b2b3c7c23ac4a1ef359748410a290bd25bbb38636f7bd2305cc6cb5d07399

The package ID was not the cause: both artifacts use com.alpha0.app.physicaltest.

## Target contract

An installable physical-test update is valid only when all of the following remain true:

1. application ID is com.alpha0.app.physicaltest;
2. the dedicated physical-test signing certificate is unchanged;
3. versionCode is monotonic;
4. the build is exact-SHA bound to staging Core;
5. the artifact manifest records the actual signing certificate SHA-256;
6. for an in-place update candidate, the caller supplies the prior stable signer SHA-256, the actual signer matches it, signerContinuityVerified=true and updateCompatible=true.

Production signing material must never be used for this channel.

## Repository support

app/build.gradle.kts now supports a dedicated test signing config through:

- SENTINEL_PHYSICAL_TEST_KEYSTORE_PATH
- SENTINEL_PHYSICAL_TEST_KEYSTORE_PASSWORD
- SENTINEL_PHYSICAL_TEST_KEY_ALIAS
- SENTINEL_PHYSICAL_TEST_KEY_PASSWORD

The routine `Physical Test APK` workflow remains deliberately secret-free, records its actual ephemeral signer certificate SHA-256, and emits `signingMode=ephemeral-debug` / `updateCompatible=false`.

The separate Owner-dispatched `Physical Test Update APK` workflow accepts these dedicated test-only GitHub Actions secrets:

- PHYSICAL_TEST_KEYSTORE_BASE64
- PHYSICAL_TEST_KEYSTORE_PASSWORD
- PHYSICAL_TEST_KEY_ALIAS
- PHYSICAL_TEST_KEY_PASSWORD

If these secrets are absent, the routine CI workflow still builds an ephemeral-debug artifact for validation, but its manifest explicitly reports `updateCompatible=false`; it must not be handed to the Owner as an in-place-update candidate. The stable-update workflow fails closed if its dedicated signing material is unavailable.

The stable workflow also accepts an optional `expected_signer_sha256` input. This value is not secret: it is the certificate fingerprint of the previously installed stable physical-test baseline. The workflow records both the actual signer and the expected signer in the manifest. A mismatch never produces an update-compatible claim.

## One-time migration consequence

The already-installed APK was signed by an ephemeral key whose private material is no longer available. The first transition to the stable physical-test signer therefore requires one uninstall/reinstall. For that first stable baseline dispatch, leave `expected_signer_sha256` empty; the resulting manifest deliberately reports `signerContinuityVerified=false` and `updateCompatible=false`, because it is a reinstall baseline rather than an in-place update.

Retain the baseline manifest/certificate SHA-256. For every later stable physical-test build, pass that prior stable signer SHA-256 as `expected_signer_sha256`. Only an exact certificate match plus a higher versionCode may be treated as an in-place-update candidate.
