# SENTINEL Artifact Attestation v1

**Status:** ACTIVE  
**Purpose:** add cryptographic GitHub/Sigstore provenance to release-readiness artifacts without expanding signing or publication authority.

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

## Publication gate

The tag-triggered `Release` workflow remains Owner-only and does not re-sign Android artifacts. Its read-only stages now require:

1. a valid protected-main `release-evidence.json` attestation for the exact tagged source commit; and
2. valid Release Candidate Artifact attestations for the APK, candidate manifest and pre-secret binding.

Candidate attestations must identify `.github/workflows/release-candidate.yml`, `refs/heads/main`, and the exact tagged source SHA. Only after lineage, APK signature, non-debuggable state, byte hashes and attestations all pass may the workflow create the publication-input artifact.

The final `publish` job remains the only job with `contents: write`. It receives no OIDC/attestation write permission, performs no checkout, executes no repository Python code and consumes only the preverified publication input.

## Permission boundary

Attestation authority is deliberately isolated:

- PR build/evidence jobs: no `id-token: write`, no `attestations: write`;
- protected-main attestation jobs: `id-token: write` + `attestations: write` (+ required artifact metadata authority), no repository secrets;
- release-candidate signing job: signing secrets, but no attestation write authority;
- release-candidate attestation job: attestation write authority, but no signing secrets;
- release publication job: `contents: write`, but no attestation/OIDC authority.

No job combines signing-key access, attestation signing authority and release publication authority.

## Fail-closed behavior

The attestation boundary rejects at least:

- missing or empty subjects;
- a different repository or workflow signer;
- a different source SHA or Git ref;
- self-hosted-runner attestations;
- a missing protected-main attestation;
- an unattested/tampered subject digest;
- mismatched packaged archive SHA-256;
- non-main or different-commit release-candidate dispatch provenance; and
- candidate bytes that differ from the signing job's exported hashes.

The existing server-side GitHub Actions artifact digest checks, deterministic release-lineage manifests, APK certificate verification, vulnerability gates and exact-SHA workflow checks remain independent defenses; artifact attestation does not replace them.

## Explicit non-claims

Repository implementation and post-merge main evidence can prove that attestation machinery works for non-secret protected-main artifacts. It does not claim that an Owner-signed release candidate exists until the Owner actually runs the signing workflow.

This contract does not authorize or perform:

- provisioning or use of production signing credentials during ordinary engineering;
- creation of a release tag;
- GitHub Release publication;
- production/live deployment;
- production secrets/credentials; or
- physical device/host/game-environment acceptance.

Those gates remain Owner/external responsibilities under canonical governance.
