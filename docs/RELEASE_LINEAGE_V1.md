# SENTINEL Release Lineage v1

**Status:** ACTIVE  
**Purpose:** bind Owner-gated Android signing and release publication to canonical exact-SHA protected-main evidence without exposing signing material to the preflight boundary.

## Invariant

A release action is valid only for one exact source commit that already has a successful protected-`main` `sentinel.release-evidence.v1` artifact. PR evidence, an older successful SHA, a debug artifact, a stale release-candidate, or an unverified local file cannot substitute for that protected-main evidence.

The lineage is:

`protected-main source SHA -> Release Evidence Preflight artifact -> pre-secret binding -> Owner-signed release candidate -> Owner tag -> read-only candidate verification -> publication authority`

## Pre-secret binding

`scripts/release_lineage.py presecret` performs the boundary before any signing secret is referenced. It:

1. requires a 40-character lowercase source SHA and canonical `VERSION`;
2. selects the newest exact-SHA `Release Evidence Preflight` run whose event is `push`, branch is `main`, workflow path is `.github/workflows/release-evidence.yml`, and conclusion is `success`;
3. requires `sentinel-release-evidence-<sha>` from that exact run;
4. downloads the GitHub artifact ZIP through the Actions API;
5. bounds the archive size and accepts only the single expected `release-evidence.json` member;
6. verifies the downloaded ZIP SHA-256 against GitHub's server-side artifact digest and size metadata;
7. runs the existing release-evidence verifier with the active Supply Chain Evidence extension against repository, exact SHA and version;
8. rejects PR evidence even if its internal structure is otherwise valid;
9. emits deterministic `sentinel.release-presecret-binding.v1` evidence.

The binding records the release-evidence workflow run/attempt, artifact identity and GitHub archive digest, internal release-evidence digest, exact source identity and explicit false claims for signing, publication and deployment. Its `bindingDigest` covers the canonical binding document.

The binding deliberately derives `generatedAt` from the immutable release-evidence manifest so repeated verification of the same evidence yields the same binding digest.

## Manual release-candidate signing

`.github/workflows/release-candidate.yml` remains an Owner-only manual workflow. It now requires an explicit `source_sha` and must itself be dispatched from `main`.

Its first job, `presecret`, has only `actions: read` and `contents: read`. It verifies the canonical protected-main evidence and exports the deterministic binding digest. The signing job has `needs: presecret`, checks out the exact selected SHA, regenerates and compares the same binding **before the first step that references release secrets**, and only then may decode the Android keystore and build the signed APK.

After independent `apksigner` fingerprint and non-debuggable verification, the workflow creates `sentinel.release-candidate.v1`. That manifest binds:

- repository, exact source SHA and version;
- pre-secret binding digest;
- release-evidence manifest digest;
- GitHub release-evidence artifact digest and run ID;
- signed APK byte size and SHA-256;
- expected signer certificate SHA-256.

The retained `sentinel-release-candidate-<sha>` artifact contains exactly:

- `app-release.apk`;
- `release-presecret-binding.json`;
- `release-candidate.json`.

Signing-key custody, secret provisioning and execution of this workflow remain Owner-only gates.

## Publication without re-signing

`.github/workflows/release.yml` remains triggered only by an Owner-created `v*.*.*` tag. It no longer decodes a keystore and no longer runs `assembleRelease`.

The workflow has three authority stages:

1. `presecret` has `actions: read` and `contents: read`. It resolves the tag to its exact commit, verifies that the tag version equals root `VERSION`, and independently verifies protected-main release evidence for that commit.
2. `verify-candidate` also has only read permissions. It regenerates the same binding, locates the newest successful `Release Candidate Artifact` workflow on `main` containing `sentinel-release-candidate-<sha>`, verifies the GitHub candidate ZIP digest/size and safe member set, validates the packaged binding/candidate/APK hashes, independently runs `apksigner`, rejects a debuggable APK, builds the exact-source Core archive, records byte hashes and uploads one preverified publication-input artifact.
3. `publish` is the **only** job with `contents: write`. It has no repository checkout and executes no repository Python code. It downloads the prior job's publication-input artifact with an immutable pinned official `actions/download-artifact` commit, rechecks the SHA-256 of every release asset against read-only job outputs, and only then calls `gh release create`.

The published assets are the already-signed APK, exact-source Core archive, release-candidate manifest, release-candidate artifact provenance and pre-secret binding.

A tag therefore cannot cause the publication workflow to manufacture a new signed binary. A valid Owner-signed release-candidate artifact for the exact tagged source SHA must already exist, and write authority is not granted until candidate verification has completed successfully.

## Fail-closed behavior

The lineage verifier rejects, among other cases:

- missing, pending, failed or non-`main` Release Evidence Preflight;
- a mismatched source SHA or version;
- expired or zero-size GitHub artifacts;
- missing/malformed GitHub SHA-256 artifact metadata;
- archive bytes whose digest/size do not match GitHub metadata;
- unsafe, nested, duplicate or unexpected ZIP paths;
- PR evidence presented as protected-main release evidence;
- tampered pre-secret binding or release-candidate manifests;
- stale candidate lineage;
- tampered APK bytes;
- unexpected signer certificate identity;
- a release-candidate workflow that did not complete successfully.

No fallback to an older successful release-evidence run is permitted when the newest exact-SHA run is failed or incomplete.

## Explicit non-claims

Repository CI can validate this boundary, schemas and synthetic tamper cases without release secrets. That does **not** mean a signed release candidate has been produced or a release has been published.

The following remain Owner/external gates:

- Android signing keystore/password custody and manual signed-RC execution;
- creation/push of the release tag;
- GitHub Release publication;
- production/live deployment;
- physical Android/Windows/audio acceptance;
- exact WoW/private-server L3 acceptance;
- production provider, ingress and database credentials.

GPT may implement, test, review and merge the lineage machinery through ordinary exact-SHA CI. GPT must stop at the actual signing, tag/publication and live-deployment gates.
