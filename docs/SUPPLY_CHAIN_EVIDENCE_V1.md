# SENTINEL Supply-Chain Evidence v1

**Status:** ACTIVE  
**Schema:** `sentinel.supply-chain-evidence.v1`

## Purpose

This contract defines machine-readable, exact-source software-component evidence for the release-candidate path. It complements vulnerability scanning, reproducible-build comparison and release signing; it does not replace any of them.

The evidence answers a narrower question: **which resolved software components were observed while building the current SENTINEL surfaces, and to which repository SHA/version are those inventories bound?**

## Evidence workflow

`.github/workflows/supply-chain-evidence.yml` runs on pull requests to `main` and pushes to `main`. It checks out the exact event source SHA and uses read-only repository permissions.

The workflow:

1. runs the repository-owned supply-chain contract tests;
2. builds the Core runtime image from the exact checkout using the production `server/Dockerfile`;
3. records the exact Docker image ID and the Python packages installed inside that runtime image;
4. generates a CycloneDX SBOM for the built Core container with the same pinned Trivy action already used by the security workflow;
5. records the Web lockfile inventory, resolved Android `debugRuntimeClasspath`, and the pinned Electron runtime identity/hash used by the packaged Companion;
6. generates a canonical CycloneDX application BOM plus `sentinel.supply-chain-evidence.v1` manifest;
7. independently verifies source binding, component counts, file digests, image identity and non-overclaim invariants; and
8. uploads `sentinel-supply-chain-evidence-<exact-source-sha>` as a retained GitHub Actions artifact.

## Application inventory semantics

`sentinel-application.cdx.json` is CycloneDX 1.6 and contains resolved/build inventories from four repository surfaces:

- `python-runtime` — packages observed with `pip list --format=json` **inside the built Core runtime image**;
- `web-lockfile` — exact package versions represented by npm lockfile v3, with development-only entries marked `excluded` rather than silently represented as shipped runtime dependencies;
- `android-debug-runtime` — resolved Maven coordinates from `:app:dependencies --configuration debugRuntimeClasspath`;
- `packaged-companion` — the exact Electron version plus the pinned upstream Windows x64 runtime SHA-256 already enforced by the Companion packaging path.

This application BOM is release-readiness dependency evidence. It is not a byte-for-byte claim that every listed build/development component is shipped in every production artifact.

## Core container SBOM

`sentinel-core-container.cdx.json` is generated from the built Core runtime image. The evidence manifest binds it to:

- the exact source repository SHA;
- the canonical `VERSION` value;
- the Docker image content ID (`sha256:...`);
- the SBOM file SHA-256; and
- its non-zero component count.

The existing reproducible-container job intentionally continues to build with BuildKit provenance/SBOM emission disabled so that its canonical filesystem comparison remains a separate, controlled reproducibility experiment. The supply-chain workflow is the dedicated inventory lane.

## Fail-closed verification

`scripts/supply_chain_evidence.py verify` rejects at least:

- malformed repository/SHA/version identity;
- missing or empty evidence inputs;
- empty Python, Web, Android or container inventories;
- invalid Electron runtime SHA-256 or Electron version drift;
- non-CycloneDX or unsupported container SBOM input;
- invalid Docker image content ID;
- missing/tampered application or container SBOM files;
- source-SHA/repository drift between the manifest and application BOM;
- component-count drift;
- malformed input digests; and
- any attempt to claim release signing, release publication, production deployment, external-environment acceptance or cryptographic attestation.

The canonical manifest also carries its own deterministic SHA-256 evidence digest.

## Relationship to release evidence

`Release Evidence Preflight` uses `scripts/release_evidence_entrypoint.py`, which extends the existing `sentinel.release-evidence.v1` policy with one additional required workflow:

- workflow: `Supply Chain Evidence`;
- required job: `Supply-chain SBOM evidence`;
- required artifact: `sentinel-supply-chain-evidence-<exact-source-sha>`.

The preflight then records GitHub's server-side SHA-256 digest for that artifact alongside the other exact-SHA release evidence. Missing, failed, stale, expired or different-SHA supply-chain evidence therefore prevents a release-preflight PASS.

## Non-claims and protected boundaries

A successful v1 supply-chain run does **not** claim:

- a signed release artifact;
- a cryptographic/Sigstore/SLSA attestation;
- signing-key or certificate custody;
- release publication;
- production deployment;
- exact target-host/device/game-environment acceptance; or
- absence of vulnerabilities by itself.

Vulnerability policy remains enforced independently by Security/P1 scans. Release signing, publication and live deployment remain Owner-only gates under canonical governance.
