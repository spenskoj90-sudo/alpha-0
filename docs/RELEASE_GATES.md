# SENTINEL Release-Candidate Gates

**Status:** ACTIVE  
**Canonical version:** root `VERSION` file  
**Evidence rule:** every applicable gate must pass on the exact commit selected for release. Missing, stale, skipped, unattested where required, or different-SHA evidence is not a pass.

## Routine pull-request gates

Routine PR validation must not load release-signing material or receive attestation-signing OIDC authority. The protected-branch contexts are:

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
12. `Repository verification` — immutable Action references, deterministic dependency metadata, signing/attestation boundaries, version and governance invariants.

The exact required context names are controlled by protected-branch policy. GPT must inspect the live policy before merge and must not change it autonomously.

In addition to the protected contexts, the release-readiness evidence program requires the exact-SHA `Supply Chain Evidence` and `Packaged Companion Host` workflows to pass. PR executions generate and verify descriptive evidence only; they do not mint attestations.

## Canonical protected-main evidence gate

A commit is eligible for Owner-gated release signing only after its protected-`main` push has a successful `Release Evidence Preflight` for that exact SHA and version.

Protected-main success is stronger than PR preflight:

- `Supply Chain Evidence` must create GitHub/Sigstore provenance for its canonical manifest and SBOM subjects in a separate no-secret downstream job.
- `Packaged Companion Host` must create GitHub/Sigstore provenance for the deterministic unsigned package and canonical package/smoke evidence subjects in a separate no-secret downstream job.
- `Release Evidence Preflight` downloads the exact artifacts named by its exact-SHA manifest, reruns their internal checks, verifies the cryptographic attestations against exact repository/workflow/SHA/ref identity, and only then uploads `release-evidence.json`.
- A downstream no-secret job then attests that `release-evidence.json` itself.

The release lineage path independently verifies the release-evidence attestation and also downloads the GitHub Actions artifact, verifies its server-side ZIP digest/size and internal manifest, and produces deterministic `sentinel.release-presecret-binding.v1` evidence.

PR evidence cannot substitute for this protected-main evidence. A stale successful main SHA cannot substitute for the explicitly selected release SHA. The cryptographic contract is defined in `docs/ARTIFACT_ATTESTATION_V1.md`.

## Release-specific artifact gate

Signing is intentionally separated from routine PR CI, attestation authority and publication:

- `.github/workflows/release-candidate.yml` is manual, must be dispatched from `main`, requires an explicit exact `source_sha`, requires `GITHUB_SHA == source_sha`, and verifies the protected-main `release-evidence.json` attestation plus canonical live evidence in a read-only `presecret` job.
- The signing job has `needs: presecret`, repeats the attestation/live binding checks before the first signing-secret reference, then builds and verifies the signed non-debuggable APK.
- The signed artifact is retained as `sentinel-release-candidate-<sha>` and contains the APK plus `sentinel.release-candidate.v1` and pre-secret lineage evidence.
- The signing job exports hashes of those exact three files. A separate downstream job receives no keystore/password secrets; it rechecks those hashes and creates GitHub/Sigstore provenance for the APK and both lineage documents.
- `.github/workflows/release.yml` runs only for an Owner-created version tag and **does not re-sign**. Its read-only stages verify the tag/version, the protected-main release-evidence attestation/live lineage, and all three candidate attestations before validating the APK signer/non-debuggable state and producing the publication input.
- The final `publish` job is the only job with `contents: write`; it has no checkout, no repository Python execution and no attestation/OIDC write authority.
- Release keystore values and signing custody remain Owner-only. A successful debug PR build or non-secret main attestation is not signed-release evidence.

The machine-verifiable details are defined in `docs/RELEASE_LINEAGE_V1.md` and `docs/ARTIFACT_ATTESTATION_V1.md`.

Before publication, the exact tagged SHA must therefore have canonical protected-main release evidence, a valid release-evidence attestation, and a successful Owner signed release-candidate workflow whose exact retained candidate bytes carry valid attestations for the same SHA. Publication itself remains an Owner gate.

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

After the Owner selects the release version, the exact commit has protected-main attested release evidence, and the Owner has run the manual signed release-candidate workflow for that exact SHA, the Owner creates and pushes an annotated tag matching `VERSION`, prefixed with `v` (for example, `v1.0.0-rc2`).

That tag invokes the publication workflow, which must consume the existing verified and attested signed candidate; it cannot create a replacement signed APK. The GitHub Release includes the verified APK, exact-source Core bundle and lineage evidence.

GPT may prepare, test, review and merge all repository machinery up to this boundary but must not provide production signing credentials, execute the signed-RC gate, create/push the release tag, publish the GitHub Release or deploy production.
