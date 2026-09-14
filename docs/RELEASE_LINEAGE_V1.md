# SENTINEL Release Lineage v1

**Status:** ACTIVE  
**Purpose:** bind Owner-gated Android signing and release publication to canonical exact-SHA protected-main evidence without exposing signing material or persisting authenticated GitHub API metadata.

## Invariant

A release action is valid only for one exact source commit that already has a successful protected-`main` `sentinel.release-evidence.v1` artifact and a valid GitHub/Sigstore attestation for that manifest. PR evidence, an older successful SHA, a debug artifact, a stale or unattested release-candidate, or an unverified local file cannot substitute for that protected-main evidence.

The lineage is:

`protected-main source SHA -> attested Supply Chain + Packaged Companion evidence -> Release Evidence verification -> attested release-evidence.json -> deterministic pre-secret binding -> Owner-signed release candidate -> no-secret candidate attestation -> Owner tag -> repeated attestation/lineage verification -> publication authority`

## Protected-main attestation prerequisite

`docs/ARTIFACT_ATTESTATION_V1.md` defines the cryptographic provenance contract. Protected-main Supply Chain and Packaged Companion workflows produce GitHub/Sigstore attestations in separate downstream jobs that have OIDC/attestation authority but no repository secrets. `Release Evidence Preflight` verifies those exact subjects before it can upload its canonical manifest, then a second no-secret job attests `release-evidence.json` itself.

`scripts/verify_release_evidence_attestation.sh` selects only a successful exact-SHA `Release Evidence Preflight` push on branch `main`, downloads its exact named artifact and verifies the manifest subject against the expected repository, `.github/workflows/release-evidence.yml`, exact source SHA, `refs/heads/main` and GitHub-hosted-runner policy.

This attestation check is additive to the existing live metadata/archive verifier; neither can substitute for the other.

## Pre-secret binding

`scripts/release_lineage.py presecret` performs the authenticated verification boundary before any signing secret is referenced. It:

1. requires a 40-character lowercase source SHA and canonical `VERSION`;
2. selects the newest exact-SHA `Release Evidence Preflight` run whose event is `push`, branch is `main`, workflow path is `.github/workflows/release-evidence.yml`, and conclusion is `success`;
3. requires `sentinel-release-evidence-<sha>` from that exact run;
4. downloads the GitHub artifact ZIP through the Actions API;
5. bounds the archive size and accepts only the single expected `release-evidence.json` member;
6. verifies the downloaded ZIP SHA-256 and size against GitHub's authenticated server-side artifact metadata;
7. runs the existing release-evidence verifier with the active Supply Chain Evidence extension against repository, exact SHA and version;
8. rejects PR evidence even if its internal structure is otherwise valid;
9. returns only a static PASS/FAIL process result and does not persist authenticated or derived data.

Owner-gated workflows run the independent GitHub attestation check before this Python boundary. After both checks succeed, `scripts/write_release_presecret_binding.sh` constructs the deterministic `sentinel.release-presecret-binding.v1` document from only the public repository/source/version identity and canonical workflow/artifact selector. The Python `verify-binding` command immediately validates the generated schema and canonical digest before the binding can be uploaded, compared, or used by later release stages.

GitHub authentication is owned by the `gh` process supplied by the workflow environment where practical. The Python lineage module never reads, receives, serializes, or logs the GitHub credential. Authenticated run/artifact metadata, server artifact digests, response sizes and release-evidence payload bytes are verification inputs only: they are validated and then discarded. They are not persisted directly, hashed into persisted lineage, or copied into the release-candidate manifest. The Python authenticated-verification path has no pre-secret binding storage sink.

The persisted binding therefore contains no raw or digest-projected authenticated API metadata. Its `bindingDigest` covers only deterministic exact-source identity, the canonical protected-main evidence selector and explicit false claims for signing, publication and deployment. Repeated generation for the same exact source is stable, but generation still fails closed unless the live protected-main evidence passes every verification step at that moment.

Repository regression tests lock this privacy boundary: persisted bindings must omit run IDs, artifact IDs, response-derived digests and timestamps; the shell-generated binding must be byte-semantically equivalent to the Python canonical binding model; candidate lineage must contain only the deterministic binding digest; and the Python authenticated path must not persist a pre-secret binding or emit data-derived values in logs.

## Manual release-candidate signing

`.github/workflows/release-candidate.yml` remains an Owner-only manual workflow. It requires an explicit `source_sha`, must itself be dispatched from `main`, and now requires `GITHUB_SHA == source_sha`.

That final requirement is a cryptographic provenance invariant: GitHub OIDC describes the workflow execution commit. The workflow cannot honestly attest a candidate as exact-source provenance if it was dispatched at one commit and merely checked out a different commit supplied as data.

Its first job, `presecret`, has read-only Actions/contents/attestation access. It verifies the protected-main release-evidence attestation, verifies canonical protected-main evidence, generates and independently verifies the deterministic binding, and exports its digest. The signing job also has read-only attestation access; it checks out the exact selected SHA, repeats both the attestation and live protected-main verification, regenerates and verifies the same binding, and compares it **before the first step that references release secrets**. Only then may it decode the Android keystore and build the signed APK.

After independent `apksigner` fingerprint and non-debuggable verification, the workflow creates `sentinel.release-candidate.v1`. That manifest binds:

- repository, exact source SHA and version;
- the deterministic pre-secret binding digest;
- signed APK byte size and SHA-256;
- expected signer certificate SHA-256;
- explicit false claims for publication and production deployment.

The retained `sentinel-release-candidate-<sha>` artifact contains exactly:

- `app-release.apk`;
- `release-presecret-binding.json`;
- `release-candidate.json`.

The signing job exports the SHA-256 of those exact bytes. A **separate downstream attestation job** has no signing secrets: it downloads the immutable candidate artifact, rechecks all three hashes and uses the pinned `actions/attest` action to attest those three subjects. Because dispatch commit identity equals `source_sha`, the GitHub OIDC source digest is the same source commit represented by the candidate lineage.

Signing-key custody, secret provisioning and execution of this workflow remain Owner-only gates. Ordinary PR/main CI validates only the machinery and non-secret attestation lanes.

## Publication without re-signing

`.github/workflows/release.yml` remains triggered only by an Owner-created `v*.*.*` tag. It does not decode a keystore and does not run `assembleRelease`.

The workflow has three authority stages:

1. `presecret` has read-only Actions/contents/attestation permissions. It resolves the tag to its exact commit, verifies that the tag version equals root `VERSION`, verifies the protected-main `release-evidence.json` attestation, repeats protected-main live release-evidence verification for that commit, constructs the deterministic public-identity binding outside the authenticated Python path, and independently verifies that binding.
2. `verify-candidate` also has only read permissions. It repeats release-evidence attestation/live verification, locates and downloads the newest successful `Release Candidate Artifact` containing `sentinel-release-candidate-<sha>`, transiently verifies GitHub candidate ZIP digest/size and safe member set, validates the packaged binding/candidate/APK, then cryptographically verifies all three candidate subjects against `.github/workflows/release-candidate.yml`, exact source SHA and `refs/heads/main`. It independently runs `apksigner`, rejects a debuggable APK, builds the exact-source Core archive, records local byte hashes and uploads one preverified publication-input artifact.
3. `publish` is the **only** job with `contents: write`. It has no repository checkout, no OIDC/attestation write authority and executes no repository Python code. It downloads the prior job's publication-input artifact with an immutable pinned official `actions/download-artifact` commit, rechecks the SHA-256 of every release asset against read-only job outputs, and only then calls `gh release create`.

The published assets are the already-signed APK, exact-source Core archive, release-candidate manifest and deterministic pre-secret binding. No authenticated GitHub API response metadata is emitted as a release asset.

A tag therefore cannot cause the publication workflow to manufacture a new signed binary or accept an unattested candidate. A valid Owner-signed and GitHub-attested release-candidate artifact for the exact tagged source SHA must already exist, and write authority is not granted until current protected-main evidence, release-evidence provenance and signed-candidate provenance have all been verified successfully.

## Fail-closed behavior

The lineage/attestation boundary rejects, among other cases:

- missing, pending, failed or non-`main` Release Evidence Preflight;
- a mismatched source SHA or version;
- expired or zero-size GitHub artifacts;
- missing/malformed GitHub SHA-256 artifact metadata;
- archive bytes whose digest/size do not match GitHub metadata;
- unsafe, nested, duplicate or unexpected ZIP paths;
- PR evidence presented as protected-main release evidence;
- missing/tampered/wrong-workflow/wrong-SHA GitHub attestations;
- self-hosted-runner attestations;
- a release-candidate dispatch whose workflow commit differs from `source_sha`;
- tampered pre-secret binding or release-candidate manifests;
- stale candidate lineage;
- tampered APK bytes;
- unexpected signer certificate identity;
- candidate bytes that differ from signing-job hash outputs; and
- a release-candidate workflow that did not complete successfully.

No fallback to an older successful release-evidence run is permitted when the newest exact-SHA run is failed or incomplete.

## Explicit non-claims

Repository CI can validate this boundary, schemas, non-secret protected-main attestations and synthetic tamper cases without release secrets. That does **not** mean a signed release candidate has been produced or a release has been published.

The following remain Owner/external gates:

- Android signing keystore/password custody and manual signed-RC execution;
- creation/push of the release tag;
- GitHub Release publication;
- production/live deployment;
- physical Android/Windows/audio acceptance;
- exact WoW/private-server L3 acceptance;
- production provider, ingress and database credentials.

GPT may implement, test, review and merge the lineage/attestation machinery through ordinary exact-SHA CI. GPT must stop at the actual signing, tag/publication and live-deployment gates.
