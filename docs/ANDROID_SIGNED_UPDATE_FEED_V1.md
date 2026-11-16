# SENTINEL Android — signed update feed v1 (SOURCE_ONLY)

This is product source and an explicit wire contract, **not** an authorized or configured distribution, new Android signing lineage, or physical acceptance. Shared custody, signing environment, historical certificate review and recovery are Owner/PROJECTS gates (existing issue #532 and draft PR #558). The separate Android observer/Stop PR is #557.

## User journey
1. Diagnostic APK and the explicitly selected `signedRelease` non-Play release variant show **Check for updates**. Without both build-pinned public values the button is disabled and states NOT_CONFIGURED; manual APK preflight remains diagnostic-only.
2. Click fetches HTTPS feed with redirects disabled and a size limit, then verifies detached ECDSA P-256 signature against a build-pinned public key. Candidate package, observed current APK signer fingerprint and same HTTPS origin are checked. A strictly higher versionCode is required before showing an update offer and the signed What's new; an authenticated **equal** versionCode instead shows "no newer version" without a download control. Older versions, invalid signatures and bad origins remain unavailable/default-deny.
3. Explicit Download first revalidates the **exact in-memory signed feed envelope**, the build-pinned HTTPS origin/public verifying key, the displayed offer, and the **current** installed package, versionCode and certificate. A forged, altered or now-obsolete offer fails **before any APK network request**. Only then does it fetch a size-limited APK without redirects and verify SHA-256; LocalApkUpdate stages a private copy, independently rechecks package, versionCode and certificate.
4. Once the downloaded APK passes staging, **both** diagnostic and `signedRelease` show a compatible APK summary and an explicit **Continue to Android installer** action; only diagnostic can manually select an APK. If Android denies unknown-source install permission, the screen provides a settings action and requires the user to return and explicitly retry. Install rechecks staged APK hash and identity and launches Android's normal system installer. No silent installation, uninstall, data erase, forced key rotation or retry bypass.

Google Play `release` builds retain their existing Play-managed in-app update path.
`signedRelease` and diagnostic channels do not initialize/register Play Update Manager
or its install listener; only the Play route uses those APIs. The signed-feed
screen remains operable on devices without Google Play Store services. The separate `signedRelease` build type keeps `com.alpha0.app`, the release signer and production security settings, but selects the signed-feed UI. Only `signedRelease` and `physicalTest` manifest overlays request `REQUEST_INSTALL_PACKAGES`; Play release does not. Android still requires explicit unknown-app-source permission and system-installer confirmation. A Play build installed from another store does not silently switch to an unpinned feed.

## Exact detached-signature wire format

HTTPS body must contain exactly three lines **plus final LF**, UTF-8, no BOM or CRLF:

    SENTINEL-SIGNED-FEED-v1
    base64url_unpadded_of_exact_manifest_bytes
    base64url_unpadded_of_DER_ECDSA_signature

Signature is SHA256withECDSA over the EXACT manifest bytes using secp256r1/P-256. Public key pin uses base64 of X.509 SPKI DER. This public verification key is NOT the Android APK signing certificate and is never fetched/rotated via an unsigned network response.

The signed manifest is exactly seven UTF-8 lines **plus final LF** in this order:

    SENTINEL-UPDATE-v1
    package=com.alpha0.app.physicaltest
    versionCode=100000895
    certificateSha256=<64 lowercase hex>
    apkUrl=https://updates.example.org/android/sentinel-v2.apk
    apkSha256=<64 lowercase hex>
    whatsNewBase64=<base64url-unpadded UTF-8 notes>

Every value above is an EXAMPLE, not a release, actual host, accepted certificate, installed app or owner decision. Notes must be non-empty, at most 1024 UTF-8 bytes and at most 12 lines. C0/C1 controls (except LF) and Unicode bidi-direction override/isolate controls are prohibited to prevent spoofed or screen-filling release announcements. Manifest cap 4096 bytes; feed cap 8192 bytes; APK cap 256 MiB. No extra/duplicate/out-of-order fields. URLs must have HTTPS and same exact feed origin, no credentials/query/fragment, no normalized path traversal, and an .apk path. No redirects or http fallback. Per-read socket timeouts are complemented by a
30-second total monotonic feed-transfer deadline and a 30-minute APK-transfer
deadline, checked on both sides of blocking stream reads. A slow trickle,
cancelled read, or clock regression fails closed; no retry or install is implied.
These are transport safety bounds, not a claim of hosted production service.

## Configuration and trust

Both public build fields default to empty, and are required together:
- SENTINEL_UPDATE_FEED_URL — fixed HTTPS feed location
- SENTINEL_UPDATE_FEED_VERIFYING_KEY — base64 DER P-256 public key

Never bundle signing private keys, APK keystores, provider tokens or recovery secrets. The feed verifying key and APK signing certificate are independent. Historical SENTINEL signer and distributed APK lineage MUST be checked before actual signed APK delivery. An empty, inaccessible or invalid feed is **NOT_CONFIGURED / UNAVAILABLE**, not proof of latest version.

## Offline feed creation (SOURCE_ONLY; NOT a publication authorization)

`scripts/signed_update_feed_release.py` is the offline producer for the exact
Android wire format above. It requires an **already signed** APK, the real Android
SDK `aapt2` and `apksigner` binaries, the highest approved distributed
`versionCode`, the independently attested exact APK SHA-256, existing
`com.alpha0.app` signer fingerprint, an embedded verified APK signature
scheme v2/v3, a reviewed
UTF-8 notes file, an exact HTTPS feed/APK origin, an approved **public** P-256
SPKI pin, and an Owner-controlled **separate** P-256 feed private-key file.
It never creates/exports keys, uploads artifacts, updates a server or invokes
Android installation. Its output file must not already exist. It rejects a
different installed-package lineage, wrong APK signer, non-increasing version,
different HTTPS origin, malformed notes, or a feed key not matching the pin.

The signer pin is fixed to the currently verified existing release identity in
source; changing that pin requires independent certificate-lineage and Owner
review. The manifest signature key is distinct from the Android APK signer.
A signed release-candidate may be processed only **after** the dedicated
release-signing/restore/Owner gates permit producing and retaining that APK.
The current release-candidate workflow still builds Play `release`, not
`signedRelease`; no non-Play artifact/feed publication is established.

`python scripts/test_signed_update_feed_release.py` exercises real OpenSSL
P-256 signing and tamper checks against **synthetic APK metadata**. These tests
cannot establish a real `apksigner` result, actual package bytes, a hosted
HTTPS feed or the same-cert over-install on either Owner device. Production
manifest generation and publication remain **NOT_RUN**.

## Evidence gate
Source/unit regressions cover tampering, wrong key, different signer, package mismatch, rollback, invalid source, malformed fields and notes. Android CI/emulator is supplemental. Before any release, require explicit owner-controlled signing/recovery acceptance, then an opt-in same-cert v1→v2 over-install without data deletion on **Infinix Zero 30** and **Poco C71**. Capture installed package, versionCode, signer, source SHA, retained local data, user consent and real device UX/accessibility. Both real-device upgrades remain **NOT_RUN** until actually performed.


## Authenticated candidate boundary

The production producer CLI now requires the dedicated non-Play GitHub run and
source SHA; a caller hash is no longer accepted. See
[ANDROID_SIGNED_FEED_CANDIDATE_V1.md](ANDROID_SIGNED_FEED_CANDIDATE_V1.md) for the
separate presecret, compiled APK, attestation and Owner approval contract. Older
`--expected-apk-sha256` invocation examples are superseded. No publication is enabled.
