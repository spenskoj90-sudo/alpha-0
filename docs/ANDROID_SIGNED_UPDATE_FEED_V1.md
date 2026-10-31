# SENTINEL Android — signed update feed v1 (SOURCE_ONLY)

This is product source and an explicit wire contract, **not** an authorized or configured distribution, new Android signing lineage, or physical acceptance. Shared custody, signing environment, historical certificate review and recovery are Owner/PROJECTS gates (existing issue #532 and draft PR #558). The separate Android observer/Stop PR is #557.

## User journey
1. Diagnostic Android Updates shows Check for updates only when a public feed URL and public verifying key are configured. Unconfigured builds show a clear blocked explanation and retain existing manual APK preflight.
2. Click fetches HTTPS feed with redirects disabled and a size limit, then verifies detached ECDSA P-256 signature against a build-pinned public key. Candidate package, versionCode strictly higher than installed, observed current APK signer fingerprint and same HTTPS origin are checked before showing the signed What's new.
3. Explicit Download click fetches a size-limited APK without redirects and verifies SHA-256; LocalApkUpdate stages a private copy, independently rechecks package, versionCode and certificate.
4. Explicit Install click rechecks staged APK hash and identity and launches Android's normal system installer. No silent installation, uninstall, data erase, forced key rotation or retry bypass.

Google Play release builds retain their existing Play-managed in-app update path.

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

Every value above is an EXAMPLE, not a release, actual host, accepted certificate, installed app or owner decision. Notes must be non-empty, printable Unicode (optional LF), at most 1024 UTF-8 bytes. Manifest cap 4096 bytes; feed cap 8192 bytes; APK cap 256 MiB. No extra/duplicate/out-of-order fields. URLs must have HTTPS and same exact feed origin, no credentials/query/fragment, no normalized path traversal, and an .apk path. No redirects or http fallback.

## Configuration and trust

Both public build fields default to empty, and are required together:
- SENTINEL_UPDATE_FEED_URL — fixed HTTPS feed location
- SENTINEL_UPDATE_FEED_VERIFYING_KEY — base64 DER P-256 public key

Never bundle signing private keys, APK keystores, provider tokens or recovery secrets. The feed verifying key and APK signing certificate are independent. Historical SENTINEL signer and distributed APK lineage MUST be checked before actual signed APK delivery. An empty, inaccessible or invalid feed is **NOT_CONFIGURED / UNAVAILABLE**, not proof of latest version.

## Evidence gate
Source/unit regressions cover tampering, wrong key, different signer, package mismatch, rollback, invalid source, malformed fields and notes. Android CI/emulator is supplemental. Before any release, require explicit owner-controlled signing/recovery acceptance, then an opt-in same-cert v1→v2 over-install without data deletion on **Infinix Zero 30** and **Poco C71**. Capture installed package, versionCode, signer, source SHA, retained local data, user consent and real device UX/accessibility. Both real-device upgrades remain **NOT_RUN** until actually performed.
