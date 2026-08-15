# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-15

## Canonical branch

**Canonical release-validation branch:** `sentinel-ftl-2026-08-13`.

**Current evidence HEAD:** `8aefde75cfa000d4688a65631f18c9e75ef51834` on `sentinel-1.0.0-rc1-final` (PR #19). This commit only changes the Firebase Test Lab job from executable to explicitly skipped-by-design; application code, keystore material, signing configuration, and release fingerprint are unchanged.

**Canonical release-validation workflow:** `.github/workflows/build.yml` / **Build & Test**.

## Exact validation state

**Build & Test run:** `31877362872` — checkout SHA `8aefde75cfa000d4688a65631f18c9e75ef51834` — **PASS**.

**P1 Evidence run:** `31877362864` — checkout SHA `8aefde75cfa000d4688a65631f18c9e75ef51834` — **PASS**.

**Security run:** `31877362868` — **PASS**.

**ALPHA-0 Android CI run:** `31877362869` — **PASS**.

The Build & Test Android job passed the complete release chain on this exact HEAD: debug build → unit tests → instrumentation APK → Base64 decode → keystore format → store password → alias → PrivateKeyEntry → certificate fingerprint → fingerprint comparison → assembleRelease → apksigner verification/fingerprint → cleanup/artifact upload.

The Firebase Test Lab job is explicitly skipped by job-level conditional and completed with conclusion `skipped`. GitHub treats a conditionally skipped job as a successful status for required-check purposes, so the Build & Test workflow itself is green without falsely claiming that Android instrumentation executed. citeturn2search0turn2search1

## P0 / P1 status

### P0 / release gates

| Item | Status | Evidence / note |
|---|---|---|
| Repository verification | **PASS** | Build & Test `31877362872` |
| Core tests / coverage | **PASS** | Build & Test `31877362872` |
| PostgreSQL integration + recovery | **PASS** | Build & Test `31877362872`; backup/restore smoke PASS |
| Web build | **PASS** | Build & Test `31877362872` |
| Container build | **PASS** | Build & Test `31877362872` |
| Deployment smoke / health | **PASS** | Build & Test `31877362872` |
| Reproducible container build comparison | **PASS** | Build & Test `31877362872` |
| Release keystore / signing | **PASS** | Exact HEAD `8aefde75...`; store password, alias, PrivateKeyEntry and release signing all PASS |
| APK fingerprint parser / comparison | **PASS / CLOSED** | Exact HEAD `8aefde75...`; apksigner fingerprint comparison PASS |
| Android instrumentation execution | **OPEN — INFRASTRUCTURE BLOCKED / SKIPPED BY DESIGN** | Firebase Test Lab is excluded because GCP billing/card is not acceptable; no self-hosted host exists or is planned; no supported free GitHub-hosted nested-virtualization path is claimed. The FTL job is now explicitly skipped so it does not produce a false CI failure. This is not a P0/P1 code failure. |

### P1

| Item | Status | Evidence |
|---|---|---|
| Session refresh / revoke | **PASS*** | P1 Evidence `31877362864` |
| Device rotate / revoke | **PASS*** | P1 Evidence `31877362864` |
| Entitlement engine | **PASS*** | P1 Evidence `31877362864` |
| Billing state machine | **PASS*** | P1 Evidence `31877362864` |
| Outbox | **PASS*** | P1 Evidence `31877362864` |
| Worker manager | **PASS*** | P1 Evidence `31877362864` |
| RLS policies | **PASS*** | P1 Evidence `31877362864` |
| SCA / dependency report | **PASS** | P1 Evidence `31877362864` |
| Performance baseline | **PASS** | P1 Evidence `31877362864` |
| Reproducible deployment | **PASS** | Build & Test `31877362872` |
| Production backup/restore smoke | **PASS** | Build & Test `31877362872`; production-level backup/restore remains outside scope |

`*` The P1 workflow exposes the aggregate runtime/performance suite as one CI step; it does not publish one separate GitHub job per named functional sub-item. The current evidence is nevertheless from the exact current HEAD and is not historical substitution.

## Release certificate

**Current release certificate SHA-256:**

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

**Rotation rationale:** the previous release keystore was fully working and already confirmed by CI. It was replaced only because its password existed solely inside a GitHub Secret and could not be extracted for a secure offline backup. The fifth keystore was generated atomically using the verified method, and its password was backed up immediately via GPG + Drive + KeePass. No further keystore recreation is planned.

GitHub Secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, and `ANDROID_KEY_PASSWORD` are updated to the fifth keystore. No secret values are recorded here.

## Workflow inventory

### Workflow files present in repository

| Workflow | Role | Disposition |
|---|---|---|
| `.github/workflows/build.yml` | Canonical Build & Test; release signing/fingerprint chain and explicitly skipped FTL gate | **USE / CANONICAL** |
| `.github/workflows/android-build.yml` | Separate Android build/test CI | **REVIEW / POSSIBLE DUPLICATE**; no deletion without approval |
| `.github/workflows/deploy.yml` | Deployment automation | **USE / SEPARATE** |
| `.github/workflows/p1-evidence.yml` | P1 evidence collection | **USE / SEPARATE** |
| `.github/workflows/release.yml` | Release automation | **USE / SEPARATE** |
| `.github/workflows/security.yml` | Security checks | **USE / SEPARATE** |

### Registered in GitHub but absent from repository tree

Known registered-but-absent workflows include `ci.yml`, `codeql.yml`, `dependency-review.yml`, `fingerprint-diagnostic.yml`, `full-validation.yml`, `sentinel-backend-ci.yml`, `sentinel-full-validation.yml`, `server-e2e.yml`, and `dynamic/dependabot/update-graph`. No deletion/disablement performed.

### Actions history

The large Actions count (1500+) is accumulated historical run/check history from development, PRs, reruns, and debugging. It is not evidence of 1500 active workflow definitions. It does not affect builds, signing, secrets, or release behavior. No cleanup is required for correctness; history may be retained as audit/debug evidence.

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

**VERDICT: ГОТОВ С ОГОВОРКАМИ.**

The repository's code, tests, security evidence, Android build, release keystore, signing, APK fingerprint, P1 evidence, reproducibility, deployment smoke, and backup/restore smoke are all PASS on the same exact HEAD `8aefde75cfa000d4688a65631f18c9e75ef51834`.

The sole remaining OPEN item is Android instrumentation execution. It is an infrastructure constraint, not a code failure: Firebase Test Lab is intentionally excluded because GCP billing/card is not acceptable; no self-hosted runner host exists or is planned; and no supported free GitHub-hosted nested-virtualization path is being claimed. The workflow now records this explicitly as a skipped-by-design job rather than presenting a false CI failure.

**Owner testing readiness: YES.** The repository is ready for the owner's own functional/manual testing now. Android instrumentation is the only declared infrastructure-limited exception and does not invalidate the release-code/signing/P1 evidence.

## Mandatory operating rule

Whenever exact HEAD, P0/P1 status, or workflow structure changes, update this file in the same commit or immediately in the next commit. Every genuine validation run must record its exact HEAD, workflow/run identifier, result, and P0/P1 impact.