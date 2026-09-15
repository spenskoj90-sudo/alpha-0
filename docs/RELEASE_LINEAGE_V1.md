# SENTINEL Release Lineage v1

**Status:** ACTIVE  
**Purpose:** bind Owner-gated Android signing, final physical/environment acceptance and release publication to canonical exact-SHA protected-main evidence without exposing signing material or persisting authenticated GitHub API metadata.

## Invariant

A release action is valid only for one exact source commit that already has successful protected-`main` `sentinel.release-evidence.v1` plus valid GitHub/Sigstore provenance. PR evidence, an older successful SHA, a debug artifact, a stale/unattested release candidate, a final-acceptance record for different bytes, or an unverified local file cannot substitute.

The lineage is:

`protected-main source SHA -> attested Supply Chain + Packaged Companion evidence -> Release Evidence verification -> attested release-evidence.json -> deterministic pre-secret binding -> Owner-signed release candidate -> no-secret candidate attestation -> real physical/environment acceptance bound to exact candidate/package -> no-secret final-acceptance attestation -> Owner tag -> repeated lineage/attestation/final-acceptance verification -> publication authority`

Deployment is a subsequent and stronger boundary: remote rollout additionally requires an Owner dispatch and a `deployment` final-acceptance profile for that exact release set.

## Protected-main attestation prerequisite

`docs/ARTIFACT_ATTESTATION_V1.md` defines the cryptographic provenance contract. Protected-main Supply Chain and Packaged Companion workflows produce GitHub/Sigstore attestations in separate downstream jobs that have OIDC/attestation authority but no repository secrets. `Release Evidence Preflight` verifies those exact subjects before it uploads its canonical manifest, then a second no-secret job attests `release-evidence.json` itself.

`scripts/verify_release_evidence_attestation.sh` selects only a successful exact-SHA `Release Evidence Preflight` push on branch `main`, downloads its exact named artifact and verifies the manifest against repository, `.github/workflows/release-evidence.yml`, exact source SHA, `refs/heads/main` and GitHub-hosted-runner policy.

This attestation check is additive to the existing live metadata/archive verifier; neither substitutes for the other.

## Pre-secret binding

`scripts/release_lineage.py presecret` performs the authenticated verification boundary before any signing secret is referenced. It:

1. requires a 40-character lowercase source SHA and canonical `VERSION`;
2. selects the newest exact-SHA successful protected-main `Release Evidence Preflight` run;
3. requires `sentinel-release-evidence-<sha>` from that exact run;
4. downloads the GitHub artifact ZIP through the Actions API;
5. bounds archive size and accepts only the single expected `release-evidence.json` member;
6. verifies downloaded ZIP SHA-256 and size against authenticated server-side artifact metadata;
7. runs the active release-evidence verifier against repository, exact SHA and version;
8. rejects PR evidence as protected-main evidence; and
9. returns only PASS/FAIL without persisting authenticated response metadata.

After independent attestation and live verification succeed, `scripts/write_release_presecret_binding.sh` creates deterministic `sentinel.release-presecret-binding.v1` from public repository/source/version identity and the canonical protected-main evidence selector. `verify-binding` immediately checks schema and canonical digest.

Persisted binding contains no raw or digest-projected authenticated API metadata. Its digest covers deterministic exact-source identity and explicit false claims for signing/publication/deployment. Regression tests prevent run IDs, artifact IDs, response-derived digests or timestamps from leaking into persisted pre-secret lineage.

## Manual release-candidate signing

`.github/workflows/release-candidate.yml` is Owner-only. It requires an explicit `source_sha`, dispatch from `main`, and `GITHUB_SHA == source_sha`; that last property is necessary because GitHub OIDC provenance describes the workflow execution commit.

The read-only pre-secret job verifies protected-main release-evidence attestation/live evidence and deterministic binding. The signing job repeats those checks before its first signing-secret reference. Only then may it decode the Android keystore and build the signed APK.

After independent `apksigner` fingerprint and non-debuggable verification, the workflow creates `sentinel.release-candidate.v1`, binding:

- repository, exact source SHA and version;
- deterministic pre-secret binding digest;
- signed APK byte size and SHA-256;
- expected signer certificate SHA-256;
- explicit false claims for publication and production deployment.

The retained `sentinel-release-candidate-<sha>` artifact contains exactly `app-release.apk`, `release-presecret-binding.json` and `release-candidate.json`. The signing job exports hashes of those bytes. A separate downstream job with no signing secrets rechecks the hashes and attests all three subjects.

Signing-key custody, secret provisioning and execution remain Owner-only gates. Ordinary PR/main CI validates machinery and non-secret provenance lanes only.

## Exact-candidate final acceptance

A signed candidate is necessary but no longer sufficient for publication. `docs/FINAL_RELEASE_ACCEPTANCE_V1.md` defines the next boundary.

Physical Android, packaged Windows host, exact WoW environment, microphone/acoustic and final accessibility/visual acceptance are performed late against the selected release set. Every accepted gate is machine-bound to:

- repository/source SHA/version;
- current retained candidate digest;
- exact signed APK SHA-256; and
- exact protected-main Packaged Companion archive SHA-256.

The Human Owner records those real results into `sentinel.final-release-acceptance.v1`. The Owner-dispatched `.github/workflows/final-release-acceptance.yml` must itself run from `main` with `GITHUB_SHA == source_sha`. Its read-only validation job independently re-verifies Release Evidence, current retained candidate/APK attestations and protected-main package provenance before it accepts the manifest. A separate no-secret OIDC job attests `final-release-acceptance.json`.

A newer or different candidate/package invalidates earlier acceptance automatically because publication re-fetches the current candidate and package and reruns the binding verifier. Real tests must then be rerun where byte/source binding changed; stale acceptance is never inherited merely because the semantic version is the same.

Repository tests use synthetic gate evidence only and therefore do not constitute physical/environment acceptance.

## Publication without re-signing

`.github/workflows/release.yml` is triggered only by an Owner-created `v*.*.*` tag. It does not decode a keystore and does not run `assembleRelease`.

Its authority stages are:

1. `presecret` — read-only Actions/contents/attestation access; resolves the tag to its exact commit/version, verifies protected-main release-evidence attestation/live lineage, creates and verifies the deterministic binding.
2. `verify-candidate` — read-only; repeats release-evidence checks, fetches the newest successful candidate for the exact source, validates GitHub candidate ZIP metadata/member set, binding/candidate/APK, candidate attestations, signer and non-debuggable state. It then invokes `scripts/verify_final_release_acceptance_live.sh` at minimum `publication` profile, which re-verifies Release Evidence, candidate provenance, protected-main package provenance, final-acceptance attestation and exact candidate/package binding. Only then is the exact-source Core archive built and one publication-input artifact uploaded.
3. `publish` — the only release job with `contents: write`. It has no checkout, no OIDC/attestation authority and executes no repository Python. It downloads only the preverified publication input, rechecks byte hashes for APK/Core/candidate/binding/final-acceptance, and calls `gh release create`.

Published lineage assets include the already-signed APK, exact-source Core archive, release-candidate manifest, deterministic pre-secret binding and `final-release-acceptance.json`.

A tag therefore cannot manufacture a new signed binary or bypass final physical/environment acceptance. Publication write authority is reached only after current protected-main evidence, candidate provenance and exact-candidate final acceptance all verify successfully.

## Deployment lineage

`.github/workflows/deploy.yml` consumes an exact published version tag rather than a mutable generic source selector. Before image publication it checks out that exact tag/source and requires at least `publication` final acceptance.

Remote rollout is not an automatic consequence of GitHub Release publication. It can run only after a separate Owner `workflow_dispatch`, `DEPLOY_ENABLED=true`, and successful verification of a stronger `deployment` final-acceptance profile for the exact same source/candidate/package. Deployment secrets are referenced only in the final remote job after that read-only acceptance job succeeds.

`production-traffic` is a stronger recorded acceptance profile adding target runtime-security/penetration evidence. The repository does not autonomously enable production traffic.

## Fail-closed behavior

The lineage/provenance/final-acceptance boundary rejects, among other cases:

- missing, pending, failed or non-main Release Evidence Preflight;
- mismatched source SHA/version;
- expired/zero-size GitHub artifacts;
- malformed authenticated artifact SHA-256 metadata;
- archive bytes whose digest/size differs from GitHub metadata;
- unsafe/nested/duplicate/unexpected ZIP paths;
- PR evidence presented as protected-main release evidence;
- missing/tampered/wrong-workflow/wrong-SHA attestations;
- self-hosted-runner attestations;
- release-candidate dispatch whose workflow commit differs from `source_sha`;
- tampered pre-secret/candidate/final-acceptance manifests;
- stale candidate lineage;
- tampered APK bytes or unexpected signer identity;
- candidate bytes differing from signing-job hash outputs;
- final-acceptance gate from another candidate/APK/package/source;
- missing required physical/environment gate;
- final-acceptance profile weaker than the requested publication/deployment operation; and
- an attempt to remote-deploy from automatic `release: published` instead of explicit Owner dispatch.

Do not fall back to older evidence when the current exact release-set evidence is failed, missing, stale or weaker than required.

## Explicit non-claims

Repository CI can validate schemas, synthetic tamper cases, authority wiring and non-secret protected-main provenance without signing/production secrets. That does not mean a signed candidate, real final acceptance, release or deployment exists.

The following remain Owner/external gates:

- Android signing keystore/password custody and manual signed-RC execution;
- physical Android/Windows/audio/accessibility and exact WoW/private-server acceptance;
- selected production provider/ingress/database/runtime-security evidence;
- Owner recording/dispatch of the final-acceptance manifest after real tests;
- creation/push of the release tag and GitHub Release publication;
- Owner-dispatched production/live deployment and production traffic activation.

GPT may implement, test, review and merge this machinery through ordinary exact-SHA CI. GPT must stop at actual signing, real-environment acceptance recording, tag/publication and live-deployment gates.
