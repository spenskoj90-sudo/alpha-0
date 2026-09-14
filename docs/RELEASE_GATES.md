# SENTINEL Release-Candidate Gates

**Status:** ACTIVE  
**Canonical version:** root `VERSION` file  
**Evidence rule:** every applicable gate must pass on the exact commit selected for release. Missing, stale, skipped or different-SHA evidence is not a pass.

## Routine pull-request gates

Routine PR validation must not load release-signing material. The protected-branch contexts are:

1. `Core tests and coverage` — compile plus unit/API/security tests; coverage at least 80%.
2. `PostgreSQL integration and recovery` — migrations from an empty database, persistence/RLS/session/event regressions, backup and restore smoke.
3. `Android build and tests` — debug APK, JVM tests and instrumentation APK, without signing secrets.
4. `Android instrumentation (GitHub Emulator)` — emulator assertions for the current debug/test APKs.
5. `Build Android APK` — independent debug APK build and JVM test path.
6. `Web build` — deterministic `npm ci`, Vitest tests, lint and production build.
7. `Container build`, `Reproducible container build comparison` and `Deployment smoke and health`.
8. `CodeQL` for Python and JavaScript.
9. `Dependency audit` — Python and npm dependency audits.
10. `Secret and image scan` — secret-pattern checks and Trivy filesystem scan with no HIGH/CRITICAL finding, including findings without a published fix.
11. `P1 evidence artifacts` — dependency and P1 performance/test evidence.
12. `Repository verification` — immutable Action references, deterministic dependency metadata, signing-boundary, version and governance invariants.

The exact required context names are controlled by protected-branch policy. GPT must inspect the live policy before merge and must not change it autonomously.

In addition to the protected contexts, the release-readiness evidence program requires the exact-SHA `Supply Chain Evidence` workflow to pass. It builds a Core container SBOM and a cross-surface resolved dependency BOM, verifies the `sentinel.supply-chain-evidence.v1` manifest and uploads `sentinel-supply-chain-evidence-<sha>`. `Release Evidence Preflight` treats that artifact as mandatory and records GitHub's server-side SHA-256 digest. This evidence is descriptive provenance/SBOM data, not release signing or a cryptographic attestation.

## Canonical protected-main evidence gate

A commit is eligible for Owner-gated release signing only after its protected-`main` push has a successful `Release Evidence Preflight` manifest for that exact SHA and version. The release lineage verifier downloads that GitHub artifact, verifies its server-side ZIP digest/size and internal manifest, and produces deterministic `sentinel.release-presecret-binding.v1` evidence.

PR evidence cannot substitute for this protected-main evidence. A stale successful main SHA cannot substitute for the explicitly selected release SHA.

## Release-specific artifact gate

Signing is intentionally separated from routine PR CI and from publication:

- `.github/workflows/release-candidate.yml` is manual, must be dispatched from `main`, requires an explicit exact `source_sha`, and verifies canonical protected-main evidence in a read-only `presecret` job.
- The signing job has `needs: presecret`, regenerates the same binding before the first signing-secret reference, then builds and verifies the signed non-debuggable APK.
- The signed artifact is retained as `sentinel-release-candidate-<sha>` and contains the APK plus `sentinel.release-candidate.v1` and pre-secret lineage evidence.
- `.github/workflows/release.yml` runs only for an Owner-created version tag and **does not re-sign**. It verifies the tag/version and canonical main evidence, downloads the already-signed candidate for the same exact SHA, verifies GitHub's artifact digest, candidate/APK lineage, signer certificate and non-debuggable state, then publishes that exact APK.
- Release keystore values and signing custody remain Owner-only. A successful debug PR build is not signed-release evidence.

The machine-verifiable details are defined in `docs/RELEASE_LINEAGE_V1.md`.

Before publication, the exact tagged SHA must therefore have both canonical protected-main release evidence and a successful Owner release-candidate artifact for the same SHA. Publication itself remains an Owner gate.

## Environment-level gates

Before production traffic, additionally verify:

- TLS certificate and HSTS behavior at the real ingress.
- GitHub Secret Scanning and push protection are enabled.
- Production enrollment secret and database credentials are injected externally.
- WAF/API-gateway rate limiting is enabled if more than one Core replica is used.
- Backup and restore has been exercised against the target PostgreSQL service.
- OWASP ZAP/Burp or equivalent runtime penetration testing is complete for the deployed endpoint.
- Required Companion host, physical Android device and exact target WoW environment acceptance is recorded where those surfaces are in release scope.

## Owner publication step

After the Owner selects the release version, the exact commit has protected-main evidence, and the Owner has run the manual signed release-candidate workflow for that exact SHA, the Owner creates and pushes an annotated tag matching `VERSION`, prefixed with `v` (for example, `v1.0.0-rc2`).

That tag invokes the publication workflow, which must consume the existing verified signed candidate; it cannot create a replacement signed APK. The GitHub Release includes the verified APK, exact-source Core bundle and lineage evidence.

GPT may prepare, test, review and merge all repository machinery up to this boundary but must not provide production signing credentials, execute the signed-RC gate, create/push the release tag, publish the GitHub Release or deploy production.
