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
