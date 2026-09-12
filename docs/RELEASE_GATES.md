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

## Release-specific artifact gate

Signing is intentionally separated from routine PR CI:

- `.github/workflows/release-candidate.yml` is manual and builds a retained, signed, non-debuggable APK for an explicitly selected commit.
- `.github/workflows/release.yml` runs only for an Owner-created version tag, verifies that the tag matches `VERSION`, verifies the signed release APK and then publishes the GitHub Release.
- Release keystore values and signing custody remain Owner-only. A successful debug PR build is not signed-release evidence.

Before publication, record the selected exact SHA and successful release-candidate artifact run. Publication itself remains an Owner gate.

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

After the Owner selects the release version and the exact commit has all applicable evidence, the Owner creates and pushes an annotated tag matching `VERSION`, prefixed with `v` (for example, `v1.0.0-rc2`). That tag invokes the release workflow, which publishes only the verified release APK and Core source bundle.

GPT may prepare and validate everything up to this boundary but must not create the release tag or publish the GitHub Release.
