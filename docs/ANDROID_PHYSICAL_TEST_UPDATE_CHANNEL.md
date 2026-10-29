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

The routine `Physical Test APK` workflow remains deliberately secret-free and verifies an ephemeral-debug APK **inside CI only**. It uploads a `sentinel-ci-only-physical-test-evidence-<SHA>` evidence bundle (manifest, signer report, checksum, warning), **not the APK itself**. `signingMode=ephemeral-debug` / `updateCompatible=false` means **never install**. Only the Owner-dispatched stable-update workflow can provide an installable test candidate after certificate continuity is independently proven.

The separate Owner-dispatched `Physical Test Update APK` workflow accepts these dedicated test-only GitHub Actions secrets:

- PHYSICAL_TEST_KEYSTORE_BASE64
- PHYSICAL_TEST_KEYSTORE_PASSWORD
- PHYSICAL_TEST_KEY_ALIAS
- PHYSICAL_TEST_KEY_PASSWORD

Without these Owner-managed secrets, routine CI still compiles and tests ephemeral-debug bytes but **does not distribute an installable APK**. The stable-update workflow fails closed when its dedicated signer is unavailable or does not match the pinned certificate; do not replace the installed certificate silently.

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

The routine secret-free CI build records its actual ephemeral signer fingerprint but uploads **only CI evidence**. It cannot supply a physical-update APK. Production signing material is forbidden for this channel.

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


## Same-signer retention proof (isolated emulator)

The dedicated `Android APK In-Place Update Retention` workflow builds two diagnostic
APKs and a test instrumentation APK using the runner's ephemeral debug signer,
with the same application ID and increasing versionCode. Android API 34
installs the baseline and upgrades it using `adb install -r` without uninstalling.
A diagnostic-gated instrumentation test seeds synthetic values in the
real `DeviceIdentity` AndroidKeyStore EC identity, `SecureSessionStore`
AES/GCM-encrypted session, and `AppPreferences`. The verification step checks
the same EC public-key fingerprint and signing ability, decrypted synthetic
session/device ID, preferences, and an app-private file after the update.

The same test checks `LocalApkUpdate.stage` against the actual next APK
while the baseline is installed: only the matching package, higher versionCode
and identical signing certificate yield `Ready`. It validates the staged
file digest and FileProvider read access. After Android replaces the app,
the same APK must be blocked as `VERSION_NOT_HIGHER`; app-private session,
settings and Keystore checks remain mandatory.

This synthetic proof cannot recover or attest the Owner's signing private key,
does not prove real-session server continuity, and does not establish compatibility
with an installed APK signed using a different certificate. No auth tokens,
Keystore private keys or credentials are exported from the emulator.

## Race-safe local APK handoff

The diagnostic Updates tab stages each user-selected APK under a distinct
randomized app-private cache filename, not a shared `candidate.apk` path. The
completed file is read-only. A newer selection cannot replace the file behind
an already-approved FileProvider URI. Before launching Android's installer the
app re-reads the candidate from disk, independently verifies its bounded SHA-256
against the staged receipt, its exact versionCode and the current package/signer
compatibility. Changed, removed, stale or unverifiable APK bytes fail closed;
Android still requests explicit user installation approval. This is not a
network download channel or a physical Owner-signer compatibility claim.


## 2026-10-29 — Poco C71 continuity incident and enforced distribution hold

Physical evidence retained in the Owner's **private** Google Drive confirms an
existing on-phone diagnostic install `com.alpha0.app.physicaltest`, source
`7def7527ad0a35b92a389b4e230f24e17a5d9541`, installed
`versionCode=100000893`, signer certificate SHA-256
`eb1e54508b7917e0b29ff6b386e05df1b9d9f7a29edf287be7a772aea5702239`.
It is the **only** SENTINEL test installation the Owner intends to retain.

This came from a historical ephemeral-debug GitHub runner that uploaded an
installable APK without the corresponding persistent signing private key.
The old certificate fingerprint, APK and diagnostic export do **not** contain
the private signing key. Custody of the exact old private key has **not** been
established. Android rejects same-package updates signed by unrelated keys,
even if the code, file hash and `versionCode` are otherwise valid. Signature
rotation also requires authorized old-key lineage, not merely knowledge of a
certificate fingerprint.

**Historical block (superseded for the Owner's Poco C71 by the clean-uninstall confirmation below):** no candidate for this Poco may claim update-over-install or
preservation of its Keystore/session until the *actual old private signer* is
located in approved custody, pinned, and its certificate reconciled against the
installed digest. The stable-test workflow's existing pin and version checks
are necessary but insufficient: its public manifest is not an installed-device
proof. Never forge `signerLineageVerified`, bypass Android signature checks,
publish another ephemeral installable APK, or label a new standalone app as an
update.

**Owner-only fallback if the exact old signer cannot be recovered:** review a
one-time, explicitly authorized same-package replacement after a verified
backup/recovery and re-enrollment plan, with transparent loss of the old local
Android Keystore identity. This is **not** an in-place update and is not
approved by continued engineering work alone. The Owner specifically rejected
accumulating parallel testing apps; do not initiate a second package, install,
uninstall, key rotation, server revoke or credential transfer without a
separate, concrete authorization.

The Owner-dispatched stable workflow now requires the public
`installed_signer_sha256` input in addition to `previous_version_code`.
For an existing installation (`previous_version_code > 0`), this digest must
exactly match the pinned stable-test certificate *before any signing key is
accessed*. A different digest or missing installed-certificate evidence fails
closed. For a genuinely clean first install, use `previous_version_code=0`,
`installed_signer_sha256=none` and the separate
`new_identity_approved=true` Owner-only checkbox. That path is explicitly
**NOT an update** and was **not applicable while the old app remained installed**. These inputs are Owner-supplied assertions, not cryptographic
device attestation: final on-device signer/update checks remain required.

For future first installs, establish one durable, separately backed-up,
test-only signing identity *before* delivering the first installable APK.
Subsequent update artifacts must use that exact signer and a monotonically
increasing `versionCode`, with emulator retention proof and exact-phone
upgrade-over-install acceptance. The regular `Physical Test APK` workflow is
CI-only and excludes APK bytes from upload by construction.


## 2026-10-29 Owner reset — first durable install only

The Owner has now explicitly confirmed removal of the old ephemeral-signed
physical-test app from the Poco C71. This replaces the earlier **active**
installed-package hold for that **specific device**. It does not establish
that any third-party Android install has been removed or that the signing key
exists. Do not try to recover, rotate or match the old ephemeral private key
for this clean phone.

The next physical-test APK may be the **first** installation of a new stable
test-only signing lineage, *only after* the Owner/PROJECTS signing-custody
and independent encrypted recovery gates are satisfied. The approved
first-install workflow inputs are:
`previous_version_code=0`, `installed_signer_sha256=none`,
`new_identity_approved=true`. Verify that the package is genuinely
absent on the target and that the new signer has never distributed a higher
versionCode. These flags do not create or back up a key.

The stable workflow allocates `versionCode` using the monotonic dedicated
workflow run number plus the last distributed baseline, **not Unix epoch
seconds**; future updates keep Android version-code headroom. Carry forward
the highest signed/distributed versionCode, the signer SHA-256, exact package
ID and original encrypted key recovery evidence. A successful CI-built APK
still requires a same-package same-signer **upgrade-over-install** test
retaining preferences, Android Keystore identity, and session/device binding.

This keeps the existing diagnostic app ID
`com.alpha0.app.physicaltest`. The shipping release app uses the different
permanent app ID `com.alpha0.app`; therefore it is **not** an automatic
update of the physical-test app. Ordinary beta/release testing should use
the final release package ID and the **same release signing lineage**, ideally
through Google Play internal testing. No authorization is given here to
change IDs, production signing, secrets or Play distribution.

There must be no additional owner-installable ephemeral/debug APK,
regardless of whether it is called a test, staging, candidate or release.
