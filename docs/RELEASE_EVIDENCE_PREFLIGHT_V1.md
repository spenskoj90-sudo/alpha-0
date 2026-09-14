# SENTINEL Release Evidence Preflight v1

**Status:** ACTIVE  
**Purpose:** define the repository-internal exact-SHA evidence boundary before Owner-gated signing, publication or production deployment.

## Purpose

This contract defines a repository-internal, exact-SHA release-readiness evidence boundary that runs before any Owner-gated signing, release publication or production deployment.

It consolidates already-produced GitHub Actions evidence into one machine-verifiable manifest. For protected-main pushes it additionally requires cryptographic GitHub/Sigstore attestations for the supply-chain and packaged-Companion evidence subjects selected by that manifest. It does **not** rebuild or republish the product and it does not elevate CI evidence into physical/environment acceptance.

Schema: `sentinel.release-evidence.v1`.

## Source binding

Every evidence manifest is bound to exactly one:

- repository (`owner/name`);
- 40-character source commit SHA;
- canonical `VERSION` value;
- GitHub event class: `pull_request` or protected-`main` `push`.

Artifact metadata is accepted only when GitHub reports the same `head_sha` and a server-side `sha256:` digest.

## Required pull-request evidence

Before a PR can be treated as release-preflight-clean, the collector requires the newest exact-head run for each workflow below to be `completed/success`:

- `Build & Test`;
- `Security`;
- `P1 Evidence`;
- `Packaged Companion Host`;
- `Supply Chain Evidence`;
- `ALPHA-0 Android CI`.

It also requires the GitHub Advanced Security check named `CodeQL`, from app slug `github-advanced-security`, to be successful on the exact PR head SHA.

The required job set includes Core tests/coverage, PostgreSQL recovery, Android build/tests, API 35 emulator instrumentation, Web build, Launcher runtime tests, Block D evidence, container build/reproducibility/deployment smoke, security scans, both workflow CodeQL language jobs, P1 evidence, packaged Companion evidence, supply-chain SBOM evidence and standalone Android APK validation.

PR evidence does not mint artifact attestations. This keeps pull-request execution free of `id-token: write` and `attestations: write` authority.

## Required protected-main evidence

For a `push` to `main`, the preflight requires the exact-SHA post-merge runs for:

- `Build & Test`;
- `Security`;
- `P1 Evidence`;
- `Packaged Companion Host`;
- `Supply Chain Evidence`.

`ALPHA-0 Android CI` is PR-only and therefore is not invented as a post-merge requirement. The Build & Test API 35 emulator job remains required.

On protected-main, the Supply Chain and Packaged Companion workflows also contain downstream no-secret attestation jobs. Their workflow conclusion cannot be `success` until those jobs have created GitHub/Sigstore provenance for the canonical subjects.

## Required artifacts

The collector requires and records GitHub artifact metadata for:

- `alpha-0-android-instrumentation-<sha>`;
- `block-d-operational-evidence-<sha>`;
- `sentinel-p1-evidence-<sha>`;
- `packaged-companion-host-<sha>`;
- `sentinel-supply-chain-evidence-<sha>`;
- on pull requests only, `alpha-0-debug-apk-<sha>`.

Each required artifact must:

- exist in the selected exact-SHA workflow run;
- be non-empty;
- not be expired;
- report an exact matching `head_sha`;
- expose a GitHub server-side SHA-256 digest.

Additional workflow artifacts may be recorded, but they cannot substitute for a required artifact.

## Protected-main attestation gate

After the exact-SHA collector returns a protected-main manifest and before `release-evidence.json` is uploaded, `scripts/verify_release_upstream_attestations.sh`:

1. reads the exact Supply Chain and Packaged Companion run IDs from the generated manifest;
2. downloads those exact named GitHub Actions artifacts from those exact runs;
3. reruns `scripts/supply_chain_evidence.py verify` on the downloaded supply-chain evidence;
4. rechecks packaged build/smoke source identity, unsigned claims and the archive SHA-256;
5. verifies every canonical subject with `gh attestation verify` using the expected repository, exact signer workflow, exact source SHA, `refs/heads/main` and `--deny-self-hosted-runners`.

The accepted subjects are defined in `docs/ARTIFACT_ATTESTATION_V1.md`. A missing, tampered, wrong-workflow, wrong-SHA, wrong-ref or self-hosted attestation fails the preflight and prevents release-evidence artifact upload.

Once the protected-main release-evidence artifact is uploaded, a separate no-secret downstream job attests the single `release-evidence.json` subject. Therefore the whole `Release Evidence Preflight` workflow reaches `success` on main only after upstream attestations were verified and the final release-evidence manifest itself was attested.

## Manifest integrity

The manifest includes:

- exact source identity;
- workflow run IDs and attempts;
- required job IDs and successful conclusions;
- artifact IDs, sizes, expiry state, SHA-256 digests and source SHA;
- applicable external GitHub Advanced Security evidence;
- an evidence digest computed over canonical JSON excluding only the digest field itself.

`scripts/release_evidence_entrypoint.py verify` enables the active Supply Chain Evidence policy, delegates to `scripts/release_evidence.py`, recomputes the digest and revalidates the evidence structure fail-closed.

Attestation verification remains an execution gate around the v1 manifest rather than a self-asserted manifest claim. This prevents the JSON document from claiming a signature before the downstream OIDC attestation has actually been created.

## Explicit non-claims

A PASS manifest always records these claims as false:

- `signedReleaseArtifact`;
- `releasePublished`;
- `productionDeployed`;
- `externalEnvironmentAcceptanceSatisfied`.

Changing any of those flags to true makes the v1 verifier reject the manifest.

Therefore this preflight does **not** prove or perform:

- Android release signing or signing-key custody;
- Windows code signing;
- release tag creation or GitHub Release publication;
- production/live deployment;
- physical Android acceptance;
- physical Windows-host acceptance;
- exact WoW/private-server L3 acceptance;
- microphone/acoustic or production STT/TTS acceptance;
- production payment-provider or ingress/database activation.

Those remain separate Owner/external gates.

## CI behavior

`.github/workflows/release-evidence.yml` runs concurrently with ordinary PR/main workflows and waits, with a bounded timeout, for the required sibling workflows on the exact source SHA. It never selects an older successful SHA to compensate for a newer failure.

If a required workflow is missing, pending beyond the timeout, failed, cancelled, stale, has incomplete artifact evidence, or fails the protected-main attestation gate, the preflight fails. Ordinary CI remediation must fix/rerun the failed source workflow; the evidence boundary must not be weakened to obtain PASS.

The workflow itself is not automatically added to branch protection. Branch-protection changes remain an Owner-only governance gate. GPT may nevertheless treat the preflight as an additional voluntary merge/release-readiness gate once the workflow is present on the PR head.

## Relation to release workflows

The preflight is the canonical repository-internal input to `docs/RELEASE_LINEAGE_V1.md` and `docs/ARTIFACT_ATTESTATION_V1.md`.

`release-candidate.yml` and `release.yml` remain Owner-gated paths because they involve signing authority and/or publication authority, but neither may accept unbound source state. Before signing or publication authority is reachable, those workflows first verify the protected-main `release-evidence.json` attestation, then `scripts/release_lineage.py` independently downloads the same protected-main preflight artifact, verifies GitHub's archive digest and the internal manifest, and applies the deterministic pre-secret binding rules.

The manual release-candidate workflow may reference Android signing material only in a job that depends on successful pre-secret verification. The tag publication workflow does not re-sign: it consumes an already-signed exact-SHA release candidate, verifies its GitHub/Sigstore attestation plus lineage/APK signature, and only then permits the separate publication-authority job to run.
