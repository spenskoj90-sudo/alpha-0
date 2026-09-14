# SENTINEL Final Release Acceptance v1

**Status:** ACTIVE  
**Schema:** `sentinel.final-release-acceptance.v1`  
**Purpose:** bind final physical, exact-environment and production-readiness evidence to one exact protected-main source and one exact signed release candidate.

## Why this boundary exists

Repository CI, protected-main attestations and the signed release-candidate lineage prove code/build provenance. They cannot prove that a selected physical Android device, packaged Windows host, exact WoW environment, microphone path or production service was actually exercised.

Those final tests happen late by design. Without an explicit binding boundary, individually valid evidence can still be unsafe if it comes from different source SHAs or different candidate/package bytes. This contract therefore makes **evidence consistency** machine-verifiable while keeping the underlying real-world observation a Human Owner acceptance claim.

A final-acceptance manifest is not hardware attestation and does not make a video, screenshot, test log or operator statement intrinsically trustworthy. It proves that the recorded evidence digest was accepted for the same release identity and byte set that later publication/deployment verifies.

## Release-set identity

Every manifest and every gate record is bound to all of the following:

- repository;
- exact 40-character protected-main source SHA;
- canonical `VERSION`;
- `sentinel.release-candidate.v1` `candidateDigest`;
- exact signed Android APK SHA-256;
- exact protected-main unsigned Packaged Companion archive SHA-256.

A gate from another source SHA, another signed APK/candidate, or another packaged Companion archive fails closed even if its own status says `PASS`.

The final-acceptance workflow independently re-fetches the retained Owner-signed candidate and protected-main packaged Companion, verifies their existing GitHub/Sigstore attestations, and compares those canonical values to the submitted manifest before accepting it.

## Profiles

Profiles are monotonic. A stronger profile contains every gate of the weaker profile.

### `publication`

Required before the Owner creates the release tag / publication path can succeed:

1. `android-physical` — selected physical Android release-device acceptance against the exact signed APK.
2. `companion-host` — selected real Windows packaged-host acceptance against the exact source-bound Companion archive.
3. `wow-exact-environment` — exact intended WoW/client/server L3 acceptance, using `docs/EXACT_ENVIRONMENT_L3_EVIDENCE_V1.md` where that target remains in release scope.
4. `voice-acoustic` — selected real microphone/driver/acoustic path acceptance for the packaged Companion.
5. `accessibility-visual` — final physical TalkBack plus packaged-host keyboard/NVDA/JAWS/visual/overlay acceptance as applicable to release scope.

This profile intentionally moves real-device/environment work to the final pre-release stage without allowing it to be skipped at publication time.

### `deployment`

Includes all `publication` gates plus:

- `payment-provider-network`;
- `voice-provider-network`;
- `runtime-observability-provider`;
- `production-database-recovery`;
- `production-ingress-readiness`.

The optional remote rollout job can run only after an Owner `workflow_dispatch`, `DEPLOY_ENABLED=true`, and an attested manifest satisfying at least this profile. A GitHub Release publication by itself can never trigger remote rollout.

### `production-traffic`

Includes all `deployment` gates plus:

- `runtime-security-penetration` — target runtime security/penetration evidence before production traffic is considered accepted.

This strongest profile is an acceptance record for traffic readiness. The repository does not autonomously enable production traffic.

### Optional gate

`firebase-test-lab` is allowed but never required while GitHub Emulator instrumentation remains the routine Android device gate and the external FTL IAM issue remains deferred.

## Gate record

Each `sentinel.final-release-gate.v1` record contains only bounded metadata:

- gate ID and `PASS` status;
- exact source identity;
- exact release-set binding digests;
- opaque bounded `environmentId`;
- UTC `recordedAt` timestamp;
- digest, size and allowlisted media type of retained detailed evidence;
- `retainedExternally: true`.

Free-form notes are deliberately excluded. Final acceptance must not become a new path for credentials, tokens, user identity, game chat, voice transcript, raw SavedVariables paths or other unnecessary sensitive payloads.

Detailed evidence stays outside the manifest and is referenced only by SHA-256/size/media type. The Human Owner is responsible for preserving the referenced evidence where required by the release process.

## Local preparation after real tests

The repository CLI computes bindings and evidence digests; operators should not type digests by hand.

Create one gate record per completed test:

```text
python scripts/final_release_acceptance.py gate \
  --id android-physical \
  --candidate release-candidate.json \
  --apk app-release.apk \
  --companion-sha256-file archive-sha256.txt \
  --environment-id android/release-device-01 \
  --evidence-file android-physical-evidence.zip \
  --media-type application/zip \
  --recorded-at 2026-09-14T20:00:00Z \
  --output android-physical.gate.json
```

Repeat for every required gate, then build the canonical manifest:

```text
python scripts/final_release_acceptance.py create \
  --profile publication \
  --candidate release-candidate.json \
  --apk app-release.apk \
  --companion-sha256-file archive-sha256.txt \
  --gate android-physical.gate.json \
  --gate companion-host.gate.json \
  --gate wow-exact-environment.gate.json \
  --gate voice-acoustic.gate.json \
  --gate accessibility-visual.gate.json \
  --output final-release-acceptance.json
```

The CLI rejects missing gates, duplicate/unknown gates, profile downgrade, source/candidate/package drift, malformed timestamps, unsupported media types, unbounded evidence size, unexpected schema fields and digest tampering.

## Owner workflow recording and attestation

After the real acceptance evidence exists, the Human Owner may run `.github/workflows/final-release-acceptance.yml` from **the exact selected `main` commit** with:

- exact `source_sha`;
- selected profile;
- base64 of the canonical `final-release-acceptance.json`.

The workflow fails unless `GITHUB_SHA == source_sha` and the dispatch branch is `main`. It contains no production/signing secrets and no `contents: write` permission.

Before accepting the manifest it independently:

1. verifies the protected-main Release Evidence attestation;
2. reconstructs the pre-secret binding;
3. re-fetches and validates the latest retained Owner-signed candidate for that SHA;
4. verifies candidate attestations;
5. downloads and re-verifies protected-main Supply Chain and Packaged Companion attestations;
6. compares the submitted manifest to the exact candidate APK/candidate digest and packaged archive digest;
7. verifies the exact requested acceptance profile.

Only then does it upload `sentinel-final-release-acceptance-<sha>`. A separate no-secret OIDC job attests `final-release-acceptance.json` with GitHub/Sigstore provenance.

If a newer signed candidate is produced later for the same source SHA, an older final-acceptance manifest does not silently transfer: live publication verification re-fetches the current candidate and rejects candidate/byte drift.

## Publication enforcement

`.github/workflows/release.yml` requires an attested final-acceptance artifact satisfying at least `publication` **before** the only `contents: write` publication job can run.

The publication verifier repeats release-evidence, candidate and packaged-Companion provenance checks, verifies the final-acceptance attestation, and reruns the schema/binding verifier. The accepted manifest is copied into the preverified publication input, hashed again immediately before publication, and published as release lineage evidence alongside the APK/candidate/pre-secret binding.

Therefore creating a version tag without final physical/environment acceptance causes publication to fail closed. No tag or release is created by this machinery itself; tag creation/publication remain Owner actions.

## Deployment enforcement

`.github/workflows/deploy.yml` now resolves an exact version tag and requires at least `publication` acceptance before publishing exact-source images.

Remote rollout has a stronger boundary:

- it is impossible on the `release: published` event;
- it requires a separate Owner `workflow_dispatch` with an exact version tag;
- it requires `DEPLOY_ENABLED=true` Owner configuration;
- it requires an attested `deployment`-profile final-acceptance manifest for the same candidate/source/package;
- only then may the existing Owner-managed deployment secrets be referenced by the remote job.

`production-traffic` remains an explicit stronger acceptance state after target runtime-security evidence. This contract does not autonomously switch traffic on.

## Failure-closed rules

Any of the following is a hard failure:

- manifest/source SHA differs from the signed candidate;
- candidate digest or APK bytes differ;
- Packaged Companion archive digest differs;
- required gate is missing;
- gate is duplicated or not allowed by the selected profile;
- gate was recorded against another release set;
- final manifest digest is invalid;
- final-acceptance workflow did not originate from the exact `main` SHA;
- final-acceptance artifact is missing, stale, unattested or attested by another workflow/ref/SHA;
- release publication asks for a profile weaker than `publication`;
- remote rollout asks for a profile weaker than `deployment`.

Do not weaken these checks to accommodate stale evidence. Re-run the affected real acceptance against the exact selected release set instead.

## Explicit non-claims

Repository tests for this contract use synthetic fixtures only. They do **not** claim that:

- a physical Android device has passed;
- a Windows target host has passed;
- exact WoW/private-server L3 has passed;
- microphone/acoustic behavior has passed;
- production payment/STT/TTS/Sentry/ingress/database infrastructure is configured;
- runtime penetration testing has passed;
- release signing has been executed;
- a tag/release has been published;
- production has been deployed or traffic enabled.

Those claims become valid only after the corresponding real evidence exists and the Owner records the appropriate exact-candidate acceptance profile.
