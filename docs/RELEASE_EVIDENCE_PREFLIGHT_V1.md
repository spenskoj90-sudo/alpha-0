# SENTINEL Release Evidence Preflight v1

**Status:** ACTIVE  
**Purpose:** define the repository-internal exact-SHA evidence boundary before Owner-gated signing, publication or production deployment.

## Purpose

This contract defines a repository-internal, exact-SHA release-readiness evidence boundary that runs before any Owner-gated signing, release publication or production deployment.

It consolidates already-produced GitHub Actions evidence into one machine-verifiable manifest. It does **not** rebuild or republish the product and it does not elevate CI evidence into physical/environment acceptance.

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
- `ALPHA-0 Android CI`.

It also requires the GitHub Advanced Security check named `CodeQL`, from app slug `github-advanced-security`, to be successful on the exact PR head SHA.

The required job set includes Core tests/coverage, PostgreSQL recovery, Android build/tests, API 35 emulator instrumentation, Web build, Launcher runtime tests, Block D evidence, container build/reproducibility/deployment smoke, security scans, both workflow CodeQL language jobs, P1 evidence, packaged Companion evidence and standalone Android APK validation.

## Required protected-main evidence

For a `push` to `main`, the preflight requires the exact-SHA post-merge runs for:

- `Build & Test`;
- `Security`;
- `P1 Evidence`;
- `Packaged Companion Host`.

`ALPHA-0 Android CI` is PR-only and therefore is not invented as a post-merge requirement. The Build & Test API 35 emulator job remains required.

## Required artifacts

The collector requires and records GitHub artifact metadata for:

- `alpha-0-android-instrumentation-<sha>`;
- `block-d-operational-evidence-<sha>`;
- `sentinel-p1-evidence-<sha>`;
- `packaged-companion-host-<sha>`;
- on pull requests only, `alpha-0-debug-apk-<sha>`.

Each required artifact must:

- exist in the selected exact-SHA workflow run;
- be non-empty;
- not be expired;
- report an exact matching `head_sha`;
- expose a GitHub server-side SHA-256 digest.

Additional workflow artifacts may be recorded, but they cannot substitute for a required artifact.

## Manifest integrity

The manifest includes:

- exact source identity;
- workflow run IDs and attempts;
- required job IDs and successful conclusions;
- artifact IDs, sizes, expiry state, SHA-256 digests and source SHA;
- applicable external GitHub Advanced Security evidence;
- an evidence digest computed over canonical JSON excluding only the digest field itself.

`scripts/release_evidence.py verify` recomputes the digest and revalidates the evidence structure fail-closed.

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

If a required workflow is missing, pending beyond the timeout, failed, cancelled, stale, or has incomplete artifact evidence, the preflight fails. Ordinary CI remediation must fix/rerun the failed source workflow; the evidence boundary must not be weakened to obtain PASS.

The workflow itself is not automatically added to branch protection. Branch-protection changes remain an Owner-only governance gate. GPT may nevertheless treat the preflight as an additional voluntary merge/release-readiness gate once the workflow is present on the PR head.

## Relation to release workflows

`release-candidate.yml` and `release.yml` remain separate protected paths because they require signing material and/or publication authority. This contract is intentionally usable without production credentials or signing keys and prepares a trustworthy evidence handoff for those later Owner-gated actions.
