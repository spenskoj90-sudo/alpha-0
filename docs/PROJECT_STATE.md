# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-15

## Canonical branch

**Canonical release-validation branch:** `sentinel-ftl-2026-08-13`.

**Current evidence HEAD:** `34c3534a0a03c0a10e1740803cd44a1871a474c4` on `sentinel-1.0.0-rc1-final` (PR #19). This commit is docs-only relative to the release-validation code state; the release-validation evidence below was produced on its immediate code predecessor `e070563e24b18e522d8a85f154a881942a8242cf`.

**Canonical release-validation workflow:** `.github/workflows/build.yml` / **Build & Test**.

## Exact validation state

**P1 Evidence run:** `31871298252` — checkout SHA `34c3534a0a03c0a10e1740803cd44a1871a474c4` — **PASS**.

The P1 run completed Python SCA, web SCA, Gradle dependency evidence, and the P1 runtime/performance suite successfully. The runtime/performance step executed 6 tests and passed 100%.

**Latest release-validation run before keystore rotation:** `31870519495` — checkout SHA `e070563e24b18e522d8a85f154a881942a8242cf` — all code/build/signing gates PASS through APK fingerprint verification using the previous release certificate. A new release keystore was then created atomically for backup/recovery purposes; the previous keystore was not considered defective.

Required release chain: decode → keystore format → store password → alias → PrivateKeyEntry → certificate fingerprint → comparison → assembleRelease → apksigner → APK fingerprint → Android instrumentation.

## P0 / P1 status

### P0

| Item | Status | Evidence / note |
|---|---|---|
| Release keystore / signing | **REVALIDATION REQUIRED** | New release keystore created intentionally for backup/recovery. GitHub Secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, and `ANDROID_KEY_PASSWORD` were updated. CI must now re-run the complete keystore → signing → apksigner → fingerprint chain against the new certificate. |
| APK fingerprint parser/comparison | **VERIFIED / CLOSED** | Parser fixed and normalization added; previous release validation run `31870519495` PASS. |
| Android instrumentation execution | **OPEN — INFRASTRUCTURE BLOCKED** | Firebase Test Lab is excluded because GCP billing/card is not acceptable; no self-hosted runner host exists or is planned. GitHub-hosted runners are VMs and nested virtualization is not officially supported, so no supported free hosted path is being claimed. This is not a P0/P1 code failure. |

### P1

| Item | Status | Evidence |
|---|---|---|
| Session refresh / revoke | **PASS*** | P1 Evidence run `31871298252` — aggregate P1 runtime/performance suite PASS. |
| Device rotate / revoke | **PASS*** | P1 Evidence run `31871298252` — aggregate P1 runtime/performance suite PASS. |
| Entitlement engine | **PASS*** | P1 Evidence run `31871298252` — aggregate P1 runtime/performance suite PASS. |
| Billing state machine | **PASS*** | P1 Evidence run `31871298252` — aggregate P1 runtime/performance suite PASS. |
| Outbox | **PASS*** | P1 Evidence run `31871298252` — aggregate P1 runtime/performance suite PASS. |
| Worker manager | **PASS*** | P1 Evidence run `31871298252` — aggregate P1 runtime/performance suite PASS. |
| RLS policies | **PASS*** | P1 Evidence run `31871298252` — aggregate P1 runtime/performance suite PASS. |
| SCA / dependency report | **PASS** | Python SCA, web SCA and Gradle dependency evidence completed successfully in `31871298252`. |
| Performance baseline | **PASS** | P1 runtime/performance suite in `31871298252` passed all 6 tests. |
| Reproducible deployment | **PASS** | `31870519495`: reproducible container build comparison PASS. |
| Production backup/restore smoke | **PASS** | `31870519495`: PostgreSQL backup and restore smoke test PASS. Production-level backup/restore remains outside scope. |

`*` The P1 workflow exposes the aggregate runtime/performance suite as one CI step; its log does not publish one separate GitHub job per named functional sub-item. No historical run is being substituted for the current P1 run.

## Release certificate

**Current release certificate SHA-256:**

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

**Rotation rationale:** the previous release keystore was fully working and already confirmed by CI. It was replaced only because its password existed solely inside a GitHub Secret and could not be extracted for a secure offline backup. The new keystore was generated atomically using the same verified method, with password backup completed immediately via GPG + Drive + KeePass. No further keystore recreation is planned.

GitHub Secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, and `ANDROID_KEY_PASSWORD` have been updated to the new keystore. Passwords and private key material are never recorded here.

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

**VERDICT: PENDING NEW-KEYSTORE CI VALIDATION.**

The repository remains ready for the owner's own testing, but release signing evidence must be revalidated once against the newly backed-up keystore. The only infrastructure-open item remains Android instrumentation execution, blocked by external infrastructure constraints: no Firebase Test Lab because billing/card is not acceptable, no self-hosted runner host, and no supported GitHub-hosted nested-virtualization path is being claimed.

This keystore rotation is an operational backup/recovery change, not a code defect correction. The new certificate is the expected release identity for all subsequent signing evidence.

## Mandatory operating rule

Whenever exact HEAD, P0/P1 status, or workflow structure changes, update this file in the same commit or immediately in the next commit. Every genuine validation run must record its exact HEAD, workflow/run identifier, result, and P0/P1 impact.
