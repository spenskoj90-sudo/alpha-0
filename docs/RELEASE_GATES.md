# SENTINEL Release-Candidate Gates

**Status:** ACTIVE  
**Canonical version:** root `VERSION` file  
**Evidence rule:** every applicable gate must pass on the exact commit selected for release. Missing, stale, skipped, unattested where required, different-SHA or different-candidate evidence is not a pass.

## Routine pull-request gates

Routine PR validation must not load release-signing material or receive attestation-signing OIDC authority. The protected-branch contexts are:

1. `Core tests and coverage` — compile plus non-PostgreSQL unit/API/security tests with a hard line-coverage floor of 85%.
2. `PostgreSQL integration and recovery` — migrations from an empty database, persistence/RLS/session/event regressions and backup/restore smoke; it appends PostgreSQL execution to branch-aware Core coverage and hard-fails below 90% combined lines or 85% combined branches.
3. `Android build and tests` — debug APK, JVM tests and instrumentation APK, without signing secrets.
4. `Android instrumentation (GitHub Emulator)` — emulator assertions for the current debug/test APKs.
5. `Build Android APK` — independent debug APK build and JVM test path.
6. `Web build` — deterministic `npm ci`, Vitest tests, lint and production build.
7. `Container build`, `Reproducible container build comparison` and `Deployment smoke and health`.
8. `CodeQL` for Python and JavaScript.
9. `Dependency audit` — Python and npm dependency audits.
10. `Secret and image scan` — secret-pattern checks and Trivy filesystem scan with no HIGH/CRITICAL finding, including findings without a published fix.
11. `P1 evidence artifacts` — dependency and P1 performance/test evidence.
12. `Repository verification` — immutable Action references, deterministic dependency metadata, signing/attestation/final-acceptance boundaries, version and governance invariants.
13. `Android product-shell contract` — `scripts/test_android_product_shell.py` verifies the pre-auth menu, RU/EN/System language choices, System/Light/Dark appearance choices, authenticated primary navigation, password recovery/email verification, server-driven federated-auth surfaces, Credential Manager/PKCE callback boundaries, explicit provider linking, scroll-safe onboarding, Play In-App Updates integration and monotonically advanced Android `versionCode`.

Green compilation alone is not Android product-readiness evidence. A change that removes a required route, language/theme choice, reachable onboarding action or update boundary fails the product-shell gate even if the APK still builds.

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
- Release keystore values and signing custody remain Owner-only. A successful debug PR build or non-secret main attestation is not signed-release evidence.

The machine-verifiable details are defined in `docs/RELEASE_LINEAGE_V1.md` and `docs/ARTIFACT_ATTESTATION_V1.md`.

## Final physical/environment acceptance binding

Physical and exact-environment tests are deliberately performed only in the final pre-release phase. Their late timing does not permit evidence from different builds to be mixed.

`docs/FINAL_RELEASE_ACCEPTANCE_V1.md` and `scripts/final_release_acceptance.py` define `sentinel.final-release-acceptance.v1`. Every recorded gate is bound to the same:

- repository/source SHA/version;
- signed release-candidate digest;
- signed Android APK SHA-256; and
- protected-main Packaged Companion archive SHA-256.

The profiles are monotonic:

- `publication` — physical Android, real Companion host, exact WoW L3, voice/acoustic and final accessibility/visual acceptance;
- `deployment` — publication plus selected payment/voice/observability provider network, production database recovery and ingress-readiness evidence;
- `production-traffic` — deployment plus target runtime penetration/security evidence.

Firebase Test Lab remains optional while GitHub Emulator instrumentation is the routine Android gate.

After the real tests exist, `.github/workflows/final-release-acceptance.yml` may be run by the Human Owner from the exact selected `main` SHA. It contains no signing/production secrets and no repository write authority. It independently verifies the protected-main release evidence, retained signed candidate and packaged Companion attestations, rejects source/candidate/package drift, uploads `sentinel-final-release-acceptance-<sha>`, and a separate OIDC job attests the final manifest.

Repository tests of this machinery are synthetic and do not count as physical/environment acceptance.

## Publication gate

`.github/workflows/release.yml` runs only for an Owner-created version tag and **does not re-sign**. Its read-only stages verify:

1. tag/version and exact source identity;
2. protected-main Release Evidence attestation/live lineage;
3. all retained signed-candidate attestations and APK signer/non-debuggable state;
4. the latest successful attested Final Release Acceptance artifact for the same exact source;
5. final-acceptance binding against the currently selected candidate/APK and canonical packaged Companion bytes at a minimum `publication` profile.

The accepted `final-release-acceptance.json` is copied into the preverified publication input and byte-hashed with the APK/Core/candidate/binding. The final `publish` job is still the only job with `contents: write`; it has no checkout, repository Python execution or attestation/OIDC write authority, rechecks all exact hashes, and publishes the final-acceptance manifest as release lineage evidence.

Therefore a version tag alone is insufficient: publication fails closed if final real acceptance is missing, stale, unattested or bound to another candidate/package.

## Deployment and production-traffic gates

`.github/workflows/deploy.yml` no longer permits remote rollout as an automatic side effect of `release: published`.

- Release publication may invoke exact-tag image publication only after at least `publication` acceptance is reverified.
- Manual deploy requires an exact existing `v*.*.*` tag; generic `latest` input is not accepted as source identity.
- Remote rollout can run only on a separate Owner `workflow_dispatch`, only when Owner configuration has `DEPLOY_ENABLED=true`, and only after an attested `deployment` profile for the exact release set passes.
- Only the remote job references the Owner-managed host/user/key secrets, and only after the read-only acceptance job succeeds.
- `production-traffic` is a stronger recorded state requiring runtime penetration/security evidence. The repository does not autonomously enable production traffic.

Environment-level evidence includes, as applicable, TLS/HSTS and ingress behavior, externally injected enrollment/database credentials, WAF/rate-limiting readiness, target PostgreSQL backup/restore, selected production provider network behavior, real Google/Telegram/VK account authentication and callback acceptance where enabled, runtime observability delivery, and final runtime security testing. Do not convert configuration intent into a PASS without corresponding real evidence.

## Owner publication and deployment steps

After the Owner selects the release version, protected-main attested release evidence exists, the Owner has run the signed release-candidate workflow for that exact SHA, and the real final tests have produced an attested `publication` profile for those exact candidate/package bytes, the Owner creates and pushes an annotated tag matching `VERSION`, prefixed with `v` (for example, `v1.0.0-rc2`).

That tag invokes the publication workflow, which consumes the existing verified/attested candidate and final acceptance; it cannot create a replacement signed APK or manufacture physical evidence.

A live remote rollout is a separate Owner action: after deployment-profile evidence exists, the Owner may explicitly dispatch `Deploy` for that exact published tag with the required Owner-managed deployment configuration/secrets. Publication alone never authorizes remote rollout.

GPT may prepare, test, review and merge all repository machinery up to these boundaries but must not provide production signing/deployment credentials, execute the signed-RC or final real-device acceptance gates, create/push the release tag, publish the GitHub Release, dispatch live remote rollout or enable production traffic.
