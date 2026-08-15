# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-15

## Canonical branch

**Canonical release-validation branch:** `sentinel-ftl-2026-08-13`.

**Current evidence HEAD:** `34c3534a0a03c0a10e1740803cd44a1871a474c4` on `sentinel-1.0.0-rc1-final` (PR #19). Subsequent commits update only CI/docs state for release-key rotation.

**Canonical release-validation workflow:** `.github/workflows/build.yml` / **Build & Test**.

## Exact validation state

**P1 Evidence run:** `31874460989` — **PASS**.

**Security run:** `31874461060` — **PASS**.

**ALPHA-0 Android CI run:** `31874461061` — **PASS**.

**New-keystore Build & Test run:** `31874461048` — **FAIL at keystore format validation**. The Android job successfully completed debug build, unit tests, and instrumentation APK assembly, then decoded `ANDROID_KEYSTORE_BASE64` but `keytool -list` failed with `java.io.EOFException` at the keystore format step. Therefore store-password validation, alias validation, PrivateKeyEntry validation, release assembly, apksigner verification, and fingerprint comparison were not reached in this run.

The CI log reported `ANDROID_KEYSTORE_BASE64 length: 5738`. The secret value is syntactically valid Base64 because the decode step succeeded, but the resulting byte stream is not accepted as a complete keystore by `keytool`. This is an **infrastructure/secret-material validation failure**, not evidence of an application-code failure.

**Previous release-validation run:** `31870519495` — checkout SHA `e070563e24b18e522d8a85f154a881942a8242cf` — all code/build/signing gates PASS through APK fingerprint verification using the previous release certificate. The previous keystore was fully working and was replaced only for backup/recovery reasons.

Required release chain: decode → keystore format → store password → alias → PrivateKeyEntry → certificate fingerprint → comparison → assembleRelease → apksigner → APK fingerprint → Android instrumentation.

## P0 / P1 status

### P0

| Item | Status | Evidence / note |
|---|---|---|
| Release keystore / signing | **OPEN — NEW SECRET MATERIAL NOT VALIDATED** | New keystore fingerprint is recorded below and expected in both signing comparison points in `build.yml`. CI run `31874461048` decoded the secret successfully but `keytool -list` returned `java.io.EOFException`, so the new keystore cannot yet be certified by CI. |
| APK fingerprint parser/comparison | **VERIFIED / CLOSED** | Parser fixed and normalization added; previous release validation run `31870519495` PASS. New-keystore comparison has not been reached because keystore format validation failed first. |
| Android instrumentation execution | **OPEN — INFRASTRUCTURE BLOCKED** | Firebase Test Lab is excluded because GCP billing/card is not acceptable; no self-hosted runner host exists or is planned. GitHub-hosted runners are VMs and nested virtualization is not officially supported, so no supported free hosted path is being claimed. This is not a P0/P1 code failure. |

### P1

| Item | Status | Evidence |
|---|---|---|
| Session refresh / revoke | **PASS*** | P1 Evidence run `31874460989` — aggregate P1 runtime/performance suite PASS. |
| Device rotate / revoke | **PASS*** | P1 Evidence run `31874460989` — aggregate P1 runtime/performance suite PASS. |
| Entitlement engine | **PASS*** | P1 Evidence run `31874460989` — aggregate P1 runtime/performance suite PASS. |
| Billing state machine | **PASS*** | P1 Evidence run `31874460989` — aggregate P1 runtime/performance suite PASS. |
| Outbox | **PASS*** | P1 Evidence run `31874460989` — aggregate P1 runtime/performance suite PASS. |
| Worker manager | **PASS*** | P1 Evidence run `31874460989` — aggregate P1 runtime/performance suite PASS. |
| RLS policies | **PASS*** | P1 Evidence run `31874460989` — aggregate P1 runtime/performance suite PASS. |
| SCA / dependency report | **PASS** | P1 Evidence run `31874460989` completed successfully. |
| Performance baseline | **PASS** | P1 Evidence run `31874460989` passed. |
| Reproducible deployment | **PASS** | Build & Test run `31874461048` passed the reproducible container build comparison. |
| Production backup/restore smoke | **PASS** | Build & Test run `31874461048` passed PostgreSQL backup/restore smoke. Production-level backup/restore remains outside scope. |

`*` The P1 workflow exposes the aggregate runtime/performance suite as one CI step; its log does not publish one separate GitHub job per named functional sub-item.

## Release certificate

**Current release certificate SHA-256:**

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

**Rotation rationale:** the previous release keystore was fully working and already confirmed by CI. It was replaced only because its password existed solely inside a GitHub Secret and could not be extracted for a secure offline backup. The new keystore was generated atomically using the same verified method, with password backup completed immediately via GPG + Drive + KeePass. No further keystore recreation is planned.

GitHub Secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, and `ANDROID_KEY_PASSWORD` were updated to the new keystore. The current CI result means the stored Base64 material is not yet accepted by `keytool` as a complete keystore; revalidate the secret payload against the local backed-up keystore before any further code change. Passwords and private key material are never recorded here.

## Workflow inventory

### Workflow files present in repository

| Workflow | Role | Disposition |
|---|---|---|
| `.github/workflows/build.yml` | Canonical Build & Test; release signing/fingerprint chain and FTL/instrumentation gate | **USE / CANONICAL** |
| `.github/workflows/android-build.yml` | Separate Android build/test CI | **REVIEW / POSSIBLE DUPLICATE**; no deletion without approval |
| `.github/workflows/deploy.yml` | Deployment automation | **USE / SEPARATE** |
| `.github/workflows/p1-evidence.yml` | P1 evidence collection | **USE / SEPARATE** |
| `.github/workflows/release.yml` | Release automation | **USE / SEPARATE** |
| `.github/workflows/security.yml` | Security checks | **USE / SEPARATE** |

### Registered in GitHub but absent from repository tree

Known registered-but-absent workflows include `ci.yml`, `codeql.yml`, `dependency-review.yml`, `fingerprint-diagnostic.yml`, `full-validation.yml`, `sentinel-backend-ci.yml`, `sentinel-full-validation.yml`, `server-e2e.yml`, and `dynamic/dependabot/update-graph`. No deletion/disablement performed.

## Branch inventory

| Branch | Status |
|---|---|
| `sentinel-ftl-2026-08-13` | **ACTIVE / CANONICAL** |
| `sentinel-1.0.0-rc1-final` | **OPEN PR #19 / current evidence branch** |
| `main` | **BASE / decision point** |
| `sentinel-ftl-repair-2026-08-14` | **TEMPORARY REPAIR / deletion candidate** |
| `p1-close-2026-08-13` | **STALE CANDIDATE** |
| `sentinel-fingerprint-diagnostic` | **STALE CANDIDATE** |
| `sentinel/1.0.0-rc1-gates` | **STALE CANDIDATE** |
| `sentinel-release-hardening-2026-08` | **STALE CANDIDATE** |
| `security/public-release-hardening` | **STALE CANDIDATE** |
| `agent/modernize-alpha0` | **STALE CANDIDATE** |
| `agent/sentinel-complete-platform` | **STALE CANDIDATE** |
| `automation/sentinel-pipeline` | **STALE CANDIDATE** |
| `sentinel/full-stack-builder` | **STALE CANDIDATE** |

No branches were deleted.

## Cleanup candidates — no deletion performed

1. Review whether `android-build.yml` duplicates the Android portion of `build.yml`.
2. Review/retire registered-but-absent historical workflows after trigger/history review.
3. Close/delete stale branches only after explicit approval.
4. Consolidate historical docs/reports only after repository-wide inventory.
5. Remove committed build artifacts only if found and explicitly reviewed.

## Release verdict

**VERDICT: NOT YET RELEASE-SIGNED BY NEW KEYSTORE.**

The codebase itself remains healthy: P1, security, Android CI, repository verification, core tests, PostgreSQL, web, container, reproducibility, and deployment smoke all pass on the new CI cycle. However, the new release keystore has **not** passed the first cryptographic validation gate because the GitHub Secret decodes to a byte stream that `keytool` rejects with `java.io.EOFException`.

This is not a reason to recreate the keystore again. The correct next action is to verify/rewrite the three GitHub Secret values from the already-backed-up keystore/password material, then rerun the exact same CI chain. No application-code change is indicated by the failure.

Android instrumentation remains separately **OPEN — infrastructure blocked** as previously established.

## Mandatory operating rule

Whenever exact HEAD, P0/P1 status, or workflow structure changes, update this file in the same commit or immediately in the next commit. Every genuine validation run must record its exact HEAD, workflow/run identifier, result, and P0/P1 impact.
