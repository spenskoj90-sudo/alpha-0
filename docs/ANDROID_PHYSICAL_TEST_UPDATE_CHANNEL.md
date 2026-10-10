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
5. the artifact manifest reports signingMode=stable-test and updateCompatible=true.

Production signing material must never be used for this channel.

## Repository support

app/build.gradle.kts now supports a dedicated test signing config through:

- SENTINEL_PHYSICAL_TEST_KEYSTORE_PATH
- SENTINEL_PHYSICAL_TEST_KEYSTORE_PASSWORD
- SENTINEL_PHYSICAL_TEST_KEY_ALIAS
- SENTINEL_PHYSICAL_TEST_KEY_PASSWORD

The routine `Physical Test APK` workflow remains deliberately secret-free and emits `signingMode=ephemeral-debug` / `updateCompatible=false`.

The separate Owner-dispatched `Physical Test Update APK` workflow accepts these dedicated test-only GitHub Actions secrets:

- PHYSICAL_TEST_KEYSTORE_BASE64
- PHYSICAL_TEST_KEYSTORE_PASSWORD
- PHYSICAL_TEST_KEY_ALIAS
- PHYSICAL_TEST_KEY_PASSWORD

If these secrets are absent, the routine CI workflow still builds an ephemeral-debug artifact for validation, but its manifest explicitly reports `updateCompatible=false`; it must not be handed to the Owner as an in-place-update candidate. The stable-update workflow fails closed if its dedicated signing material is unavailable.

## Owner-controlled signing transition

Preserve the installed app, its Keystore identity and its device/session binding.
Different ephemeral certificates do not support update-over-install. Do not assume
that the old private key is recoverable, and do not prescribe uninstall/reinstall
as an ordinary engineering fix. A new stable key cannot retroactively establish
the old certificate's lineage.

The Owner chooses one of these concrete paths after reviewing the installed
package/version and certificate evidence:

- If the actual old signer remains in approved custody, use it through the
  dedicated test secret store and verify the certificate plus a higher versionCode.
- If the old signer is unavailable, approve a separate durable test identity and
  package/callback migration that preserves the existing installation. A second
  package starts with its own Keystore/device registration; identity is not copied
  or silently treated as continuous. Prepare that build only after this decision.

Never request a private key or password in chat. Test custody and production
release custody are separate. `signerLineageVerified` proves the pinned build
certificate match, not compatibility with an unidentified installed app. Physical
update acceptance additionally proves retained identity and session/device recovery.

## Cross-workflow version allocation

GitHub run counters are independent for routine and stable-update workflows.
`100000000 + GITHUB_RUN_NUMBER` in the update workflow could therefore be lower
than an already installed diagnostic version (for example 100000525). The stable
workflow instead requires `previous_version_code`: the highest already distributed
code for the pinned signer, obtained from the retained manifest. Use zero only for
an explicitly approved new identity, never as an update baseline.

`scripts/physical_test_version.py` allocates the greater of current UTC epoch
seconds and that baseline plus one, refusing values above 2100000000. The artifact
verifier independently requires the APK's actual Gradle versionCode to exceed the
supplied baseline and records `updateBaselineVersionCode`. Before each dispatch,
carry forward the highest distributed code from the last manifest; a falsely low
input cannot prove device compatibility. The routine ephemeral channel keeps its
independent diagnostic counter and does not claim update compatibility.

Primary versioning contract: https://developer.android.com/studio/publish/versioning


## Signer continuity pin

The stable physical-test update workflow is fail-closed against a non-secret repository variable:

- `PHYSICAL_TEST_SIGNER_SHA256` — lowercase 64-hex SHA-256 fingerprint of the dedicated test-only signing certificate.

The workflow extracts the actual certificate fingerprint with Android `apksigner` and requires exact equality before `signerLineageVerified=true` and `updateCompatible=true` can be emitted. Replacing or rotating the test keystore without deliberately updating this pin therefore cannot silently produce an in-place-update claim.

The routine secret-free diagnostic Physical Test APK also records its actual signer fingerprint, but remains `signingMode=ephemeral-debug` and `updateCompatible=false`. Production signing material is forbidden for this channel.

## Installed identity in local diagnostics

New builds record the actual package at process start and one asynchronous
`PACKAGE_SIGNER` event from Android PackageManager. It contains actual installed
versionCode, current certificate SHA-256 digests and bounded signing-history
digests; multiple signers are distinct from rotation. No APK bytes, private key,
Keystore/device identity or automatic upload is involved. Read failures produce
`PACKAGE_SIGNER_UNAVAILABLE`, never guessed identity. Export may precede this
asynchronous event; missing evidence remains unknown and must not authorize an
update. Compare current certificate(s), package and increasing versionCode with
the retained candidate before installation, then verify identity/session recovery.

History metadata does not itself mark `updateCompatible` or prove preservation of
an older installation. The historical Infinix `cf40028f` log records code
`100000517` but has no certificate/package metadata; it cannot establish current
signer compatibility. Preserve that installation while the Owner decides custody
or a separate durable test identity. Google OAuth SHA-1 registration additionally
comes from the retained **stable** signing certificate, not an ephemeral build.

## Google OAuth Android client handoff (stable test certificate only)

The dedicated **Physical Test Update APK** workflow verifies one APK signing
certificate via Android `apksigner`, checks its SHA-256 against the pinned
`PHYSICAL_TEST_SIGNER_SHA256` repository variable, and extracts the **same
certificate's public SHA-1** fingerprint. Its signed-artifact manifest adds
`signerCertificateSha1` only for `signingMode=stable-test` after these checks.
The routine ephemeral-debug manifest must not contain that field.

After the Human Owner chooses the existing-signer/update path or deliberately
approves a separate durable test identity, use the signed manifest's exact
`apk.applicationId=com.alpha0.app.physicaltest` and
`signerCertificateSha1` to create the **Android** OAuth client in the already
configured Google Cloud SENTINEL Staging project. Preserve its existing
**Web** OAuth client ID as the Core Credential Manager audience; never replace
the Web client ID with the Android client ID.

A recorded SHA-1 is a *registration candidate*, not proof that Google Cloud
registered it, the installed Infinix app shares the signer, or Google login
worked. A missing/unverified stable test signer must leave Google disabled.
Do not issue a stable-signed APK, manipulate signing secrets or declare
`updateCompatible=true` merely to obtain a SHA-1. All signing material stays
in approved provider custody; no certificate/private-key bytes are published.

API reference: https://developer.android.com/reference/android/content/pm/SigningInfo
