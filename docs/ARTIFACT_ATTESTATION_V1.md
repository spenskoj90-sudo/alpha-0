# SENTINEL Artifact Attestation v1

**Status:** ACTIVE  
**Purpose:** add cryptographic GitHub/Sigstore provenance to release-readiness and final-acceptance artifacts without combining signing, acceptance-recording or publication authority.

## Invariant

Cryptographic provenance is accepted only when the attestation verifies the artifact bytes and the certificate identity is bound to:

- repository `spenskoj90-sudo/alpha-0` (or the current `GITHUB_REPOSITORY` value in workflow execution);
- the expected repository-owned workflow path;
- the exact source commit SHA;
- the explicit Git ref that supplied the workflow execution; and
- a GitHub-hosted runner.

Verification uses `gh attestation verify` with `--repo`, `--signer-workflow`, `--source-digest`, `--source-ref` and `--deny-self-hosted-runners`. A repository match alone is not sufficient.

The attestation producer is the immutable pinned `actions/attest` v4 commit. GitHub Actions OIDC supplies a short-lived signing identity; no long-lived attestation signing key is stored in the repository.

## Protected-main evidence subjects

Ordinary pull-request workflows remain read-only and do not receive OIDC or attestation write authority. On a successful `push` to `main`, separate downstream jobs attest already-verified immutable workflow artifacts.

`Supply Chain Evidence` attests:

- `supply-chain-evidence.json`;
- `sentinel-application.cdx.json`;
- `sentinel-core-container.cdx.json`.

`Packaged Companion Host` attests:

- `sentinel-companion-win32-x64.zip`;
- `build-evidence.json`;
- `package-manifest.sha256`;
- `smoke-evidence.json`;
- `archive-sha256.txt`.

The packaging workflow stages those files into one stable artifact layout. The archive SHA-256 is emitted as a canonical lowercase digest and is rechecked before attestation.

## Release Evidence gate

For protected-main pushes, `Release Evidence Preflight` first waits for the exact-SHA Supply Chain and Packaged Companion workflows to complete successfully. It downloads the exact artifacts selected by the generated release-evidence manifest, revalidates the supply-chain contract and packaged archive digest/source claims, and cryptographically verifies every required attestation subject.

Only after those checks pass may it upload `sentinel-release-evidence-<sha>`. A separate downstream no-secret attestation job then attests the single `release-evidence.json` subject.

Pull-request release evidence continues to validate exact-head workflow/job/artifact state but does not mint attestations. This keeps PR execution free of OIDC/attestation write authority.

## Owner-signed release candidate

`Release Candidate Artifact` remains Owner-only. A dispatch is accepted only when:

- the workflow is dispatched from `main`;
- `source_sha` is a valid exact SHA; and
- `GITHUB_SHA == source_sha`.

The last invariant is required because GitHub OIDC provenance describes the workflow execution commit. Allowing the job to attest an arbitrary checkout SHA while the workflow itself ran at another commit would weaken the cryptographic source claim.

Before signing-secret access, the workflow verifies both the protected-main release-evidence attestation and the existing live release-lineage checks. After the signed APK and deterministic candidate manifests are built and verified, their SHA-256 values are exported. A separate downstream job with no signing secrets downloads the immutable candidate artifact, rechecks those hashes, and attests exactly:

- `app-release.apk`;
- `release-candidate.json`;
- `release-presecret-binding.json`.

The attestation job has no keystore/password input and no publication authority.

## Final Release Acceptance subject

Real physical/environment evidence is recorded only after those tests actually happen. `.github/workflows/final-release-acceptance.yml` is an Owner-dispatched, no-secret workflow that binds the submitted `sentinel.final-release-acceptance.v1` manifest to the exact protected-main source, current retained signed candidate/APK and canonical protected-main Packaged Companion archive.

The validation job is read-only. It requires dispatch from `main` with `GITHUB_SHA == source_sha`, independently verifies the Release Evidence, signed-candidate and packaged-Companion provenance chains, then runs the final-acceptance schema/binding verifier. It has no signing secrets, no deployment secrets and no `contents: write` permission.

Only after validation succeeds is `final-release-acceptance.json` uploaded as `sentinel-final-release-acceptance-<sha>`. A separate downstream job with no secrets downloads that single immutable subject and attests it using GitHub OIDC. The source identity of that attestation is therefore the exact `main` commit whose signed/package bytes the manifest references.

`scripts/verify_final_release_acceptance_attestation.sh` accepts only a successful workflow-dispatch execution of `.github/workflows/final-release-acceptance.yml` for the exact source SHA on `main`, downloads the exact named artifact, requires exactly one `final-release-acceptance.json`, and verifies the attestation against repository/workflow/SHA/ref/GitHub-hosted-runner policy.

A cryptographic final-acceptance attestation proves provenance of the accepted manifest bytes. It does not independently prove that a physical test happened; the Human Owner remains responsible for the underlying retained evidence and the truth of the real-environment acceptance claim.

## Publication gate

The tag-triggered `Release` workflow remains Owner-only and does not re-sign Android artifacts. Its read-only stages require:

1. a valid protected-main `release-evidence.json` attestation for the exact tagged source commit;
2. valid Release Candidate Artifact attestations for the APK, candidate manifest and pre-secret binding; and
3. a valid Final Release Acceptance attestation whose manifest independently verifies against those exact candidate/APK bytes and the protected-main packaged Companion archive at minimum `publication` profile.

Candidate attestations must identify `.github/workflows/release-candidate.yml`, `refs/heads/main`, and the exact tagged source SHA. Final acceptance must identify `.github/workflows/final-release-acceptance.yml`, `refs/heads/main`, and the same exact source SHA.

Only after lineage, APK signature, non-debuggable state, byte hashes, all prior attestations and final physical/environment binding pass may the workflow create the publication-input artifact. `final-release-acceptance.json` is itself included and byte-hashed in that publication input.

The final `publish` job remains the only release job with `contents: write`. It receives no OIDC/attestation write permission, performs no checkout, executes no repository Python code and consumes only the preverified publication input.

## Permission boundary

Authority is deliberately isolated:

- PR build/evidence jobs: no `id-token: write`, no `attestations: write`;
- protected-main supply/package/release-evidence attestation jobs: OIDC + attestation write authority, no repository secrets;
- release-candidate signing job: signing secrets, but no attestation write authority;
- release-candidate attestation job: attestation write authority, but no signing secrets;
- final-acceptance validation job: read-only Actions/contents/attestations, no signing/deployment secrets and no OIDC signing authority;
- final-acceptance attestation job: OIDC + attestation write authority, no signing/deployment secrets and no repository write authority;
- release publication job: `contents: write`, but no signing secrets and no attestation/OIDC authority;
- remote deployment job: Owner-dispatched and gated by stronger final-acceptance verification before deployment secrets are referenced; it has no attestation signing or release-publication authority.

No job combines signing-key access, attestation signing authority, final-acceptance validation and release publication authority.

## Fail-closed behavior

The attestation boundary rejects at least:

- missing or empty subjects;
- a different repository or workflow signer;
- a different source SHA or Git ref;
- self-hosted-runner attestations;
- a missing protected-main attestation;
- an unattested/tampered subject digest;
- mismatched packaged archive SHA-256;
- non-main or different-commit release-candidate dispatch provenance;
- candidate bytes that differ from the signing job's exported hashes;
- final acceptance from another source SHA, signed candidate/APK or packaged Companion archive;
- an unattested/stale/missing final-acceptance manifest; and
- a final-acceptance profile weaker than the publication/deployment operation requires.

The existing server-side GitHub Actions artifact digest checks, deterministic release-lineage manifests, APK certificate verification, vulnerability gates and exact-SHA workflow checks remain independent defenses; artifact attestation does not replace them.

## Explicit non-claims

Repository implementation and post-merge main evidence can prove that attestation machinery works for non-secret protected-main artifacts. Repository tests can prove final-acceptance schemas and authority wiring using synthetic fixtures. Neither claims that an Owner-signed release candidate or real final-acceptance artifact exists until the Owner actually performs the corresponding signing/tests/workflow dispatch.

This contract does not authorize or perform:

- provisioning or use of production signing credentials during ordinary engineering;
- physical Android/Windows/audio/WoW/provider/production-environment acceptance;
- creation of a release tag;
- GitHub Release publication;
- production/live deployment or production traffic activation; or
- production secrets/credentials.

Those remain Owner/external gates under canonical governance and `docs/FINAL_RELEASE_ACCEPTANCE_V1.md`.
