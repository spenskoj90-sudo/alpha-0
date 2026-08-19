# SENTINEL — Project State

Updated: 2026-08-15
Commit: e070563e24b18e522d8a85f154a881942a8242cf
Branch: sentinel-ftl-2026-08-13

## CI fingerprint fix

The release APK fingerprint comparator in `.github/workflows/build.yml` was fixed by normalizing both `expected` and `actual` values before comparison: remove `:` and normalize case. Original values remain unchanged in the log output.

Commit diff is limited to the requested comparator step: two normalized variables were added and the comparison now uses them.

## Validation

- Repository verification: PASS
- Core tests and coverage: PASS
- PostgreSQL integration and recovery: PASS
- Web build: PASS
- Container build: PASS
- Reproducible container build comparison: PASS
- Deployment smoke and health: PASS
- Android assembleDebug: PASS
- Android unit tests: PASS
- Android instrumentation APK build: PASS
- Keystore validation: PASS
- Release APK assembly: PASS
- Release APK signature/fingerprint verification: PASS

## Firebase Test Lab

FTL job reached authentication and failed before any device test because `google-github-actions/auth@v2` received neither `workload_identity_provider` nor `credentials_json`. This is an environment/secret configuration blocker, not a code or APK-signing failure.

The generated instrumentation artifacts were downloaded successfully before authentication.

## P1 revalidation

Latest completed P1 Evidence run: `31677563500` (2026-08-13), all P1 evidence steps PASS, including Python SCA, web SCA, Gradle dependency report, and P1 runtime/performance tests.

The current commit changes only CI fingerprint comparison logic and does not modify application/runtime code. P1 impact revalidation: PASS.

## Release gate

Current release gate: BLOCKED only by Firebase Test Lab Google authentication configuration. The APK fingerprint defect is resolved and independently verified by the CI release-signature step.
