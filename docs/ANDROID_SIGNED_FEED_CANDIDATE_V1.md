# Non-Play signedRelease candidate boundary v1

This is a separate, Owner-gated preparation/verification lane. It does not publish
an APK/feed, dispatch a workflow, merge, change signing lineage or replace final
acceptance. PROJECTS #532 owns origin approval, permanent P-256 custody, distribution
ledger and provider/production gates. Historical A+B RESTORE_PASS is retained.

## Identity and independent approval

`.github/workflows/signed-feed-candidate.yml` is dispatch-only on the exact current
protected-main SHA. It verifies attested canonical release evidence and independently
retrieves the existing Play baseline from authenticated GitHub run/artifact metadata,
checks archive digest/size, exact files, all three attestations and actual APK
package/version/signer. A caller-provided APK SHA does not grant authority.

The workflow requires a **separate reviewed protected-main source record** at
`release/signed-feed-approval.json`. No approved record, origin or pin is supplied
by this PR. Missing approval deliberately blocks signing. The exact fields are:

- `schema`: `sentinel.signed-feed-approval.v1`; `status`: `APPROVED`;
- `reviewIssue`: 532; `channel`: `signed_feed`; `package`: `com.alpha0.app`;
- `signer`: `2acd1cfff4f34db1250d3f6c81f0887493c4602d3cfa65310993c058089db88e`;
- independently approved `apiBaseUrl` (strict HTTPS origin) and `vkClientId` and `telegramClientId` (canonical decimal, `0` when disabled), plus `googleClientId` (empty when disabled); fallback is empty and OAuth callback scheme is fixed to `com.alpha0.app.auth`;
- independently approved exact `feedUrl` and Base64 named P-256 DER SPKI `verifyingKey`;
- independently reconciled `highestIssuedVersionCode` (at least 10007);
- `baselineSourceSha` and `baselineApkSha256` for the independently retained baseline.

The record is an Owner-reviewed release decision, not an automatically inferred
highest-ever distribution ledger. It must be reconciled before each future signing
campaign. Version 10008 is now source-selected; the gate refuses it if the reviewed
ledger has already reached that code. A new source increment is then required.

## Before protected secrets

The secret-free job checks approval/evidence/baseline, builds signedRelease with a
one-day isolated test-only keystore, then inspects real merged APK badging,
REQUEST_INSTALL_PACKAGES, non-debuggable state and typed static BuildConfig fields
inside actual DEX. The non-Play-only R8 rule retains that class. This checks exact
source SHA, package, versionCode, channel, feed URL and public SPKI, rather than
searching for unrelated strings. The binding records a digest of every unpacked
payload entry except APK signature metadata. It transfers the inspected payload
and binding within the same workflow run. It never distributes the test APK.

The protected-environment job revalidates the same independent evidence, approval,
compiled payload and binding digest **before** accessing the existing signer.
It signs the already inspected payload with apksigner, without passing protected
keys to Gradle or rebuilding product code. Actual single certificate and v2/v3
verification, package/version/permission, typed constants and payload continuity
must pass again. Ephemeral presecret keys are never a release lineage.

## Separate names and attestation consumers

- workflow: `Signed Feed Candidate Artifact`, `signed-feed-candidate.yml`;
- retained artifact: `sentinel-signed-feed-candidate-<sourceSha>`;
- archive members: `app-signedRelease.apk`, `signed-feed-candidate.json`,
  `signed-feed-presecret-binding.json`;
- schemas: `sentinel.signed-feed-candidate.v1` and
  `sentinel.signed-feed-presecret-binding.v1`;
- both records bind `channel=signed_feed`, `distribution=non_play`.

A separate OIDC job attests all three exact subjects after rechecking the signing
job's hashes. The `scripts/signed_feed_candidate.py fetch` consumer requires an
explicit dedicated successful run, authenticated artifact ID/run/digest/size,
strict archive membership and GitHub attestation verification constrained to repo,
dedicated workflow, main ref and exact source digest, denying self-hosted runners.
It then independently repeats presecret and actual APK inspection.

Production `signed_update_feed_release.py` CLI requires `--candidate-source-sha`
and `--candidate-run-id`, consumes that verified candidate and binds feed inputs to
its approved policy. It no longer accepts `--expected-apk-sha256`. The internal
`make` primitive is only a wire/crypto primitive, not an attestation verifier.
No feed-signing key may be used until that authenticated CLI boundary succeeds.

Existing Play workflow, artifact filenames, `sentinel.release-candidate.v1`,
`fetch-candidate`, `release.yml` and final acceptance are byte-preserved. The new
non-Play artifact cannot satisfy their workflow/schema/archive requirements.
Byte-contract regressions pin those existing consumers independently of clone depth.
There is **no new non-Play publication or final-acceptance route** in this package.

## Evidence scope

Local Python fixtures use synthetic APK metadata, minimal encoded DEX and mocked
GitHub responses/attestations with real ephemeral OpenSSL public-key inspection.
They establish rejection contracts, not a real protected signed APK or attestation.
A protected-main run is deliberately NOT_RUN: no signing dispatch is authorized.
Real approved signedRelease bytes, origin/SPKI, hosted feed, physical same-cert
upgrade/data retention, native TalkBack and OWNER_ACCEPTED remain separate gates.

Ordinary Android CI additionally exercises real SDK aapt2/apksigner and the actual
minified signedRelease DEX using disposable test-only keys. It explicitly rejects
that certificate as the protected signer. Only `signed-feed-ci-receipt.json`
(source/APK/payload/certificate hashes, CI_ONLY and false publication/lineage claims)
is retained alongside the existing CI evidence; the installable test APK is deleted.

The Core origin and VK client ID are read only from the reviewed source policy,
not dispatch inputs. Actual DEX constants for Core URL, empty fallback, the
generic callback scheme, and exact VK redirect are compared to that policy
before signer access and again by the consumer. Google challenge client IDs are compared with the reviewed DEX-pinned `googleClientId` before Credential Manager is invoked. An empty pin disables Google for signed_feed; other channels retain their existing server-managed behavior. Core provider settings still require separate verification. No real origin or
OAuth ID is approved by these changes.

For signed_feed, reviewed `telegramClientId` and `vkClientId` are also retained
in DEX and compared against the provider catalogue. Zero disables a provider.
Before opening a browser, the actual authorization URL must match the pinned
client ID, exact provider endpoint/redirect, state, expected scope and SHA-256
PKCE challenge, and contain no duplicate or extra query parameters. Telegram's
nonce must match state. Other channels retain their existing behavior. Provider
server-side credentials and deployment are separate gates.
