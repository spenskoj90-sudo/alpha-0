# SENTINEL — PROJECT STATE

Single source of truth for release-validation, repository hygiene, and owner-testing readiness.

**Last updated:** 2026-08-15

## Canonical branches / evidence

- **Canonical release-validation branch:** `sentinel-ftl-2026-08-13`.
- **Current evidence branch:** `sentinel-1.0.0-rc1-final` (PR #19).
- **Latest application/workflow evidence HEAD:** `8aefde75cfa000d4688a65631f18c9e75ef51834`.
- Documentation-only updates may advance the branch HEAD; they do not replace the exact code/workflow HEAD cited by validation evidence.
- `main` remains the base/decision point; no branch deletion or merge was performed.

## Canonical workflow

`.github/workflows/build.yml` / **Build & Test** is the canonical release-validation workflow.

## Validation evidence

- Build & Test `31877362872` — checkout SHA `8aefde75cfa000d4688a65631f18c9e75ef51834` — **PASS**.
- P1 Evidence `31877362864` — same checkout SHA — **PASS**.
- Security `31877362868` — **PASS**.
- ALPHA-0 Android CI `31877362869` — **PASS**.

The Build & Test Android release chain passed on the exact evidence HEAD: debug build, unit tests, instrumentation APK build, keystore Base64 decode, PKCS12 format, store password, alias, PrivateKeyEntry, certificate fingerprint, fingerprint comparison, assembleRelease, apksigner verification/fingerprint, cleanup and artifact upload.

Firebase Test Lab is **not used**. Android instrumentation through external CI remains **OPEN — infrastructure blocked / deferred by decision**. No GCP billing/card, no self-hosted runner host, and no supported free hosted nested-virtualization path is available/planned. This is not a P0/P1 code failure.

## P0 / release gates

| Item | Status | Evidence |
|---|---|---|
| Repository verification | PASS | Build & Test `31877362872` |
| Core tests / coverage | PASS | Build & Test `31877362872` |
| PostgreSQL integration + recovery | PASS | Build & Test `31877362872` |
| Web build | PASS | Build & Test `31877362872` |
| Container build | PASS | Build & Test `31877362872` |
| Deployment smoke / health | PASS | Build & Test `31877362872` |
| Reproducible container comparison | PASS | Build & Test `31877362872` |
| Release keystore / signing | PASS | Exact evidence HEAD `8aefde75...` |
| APK fingerprint parser / comparison | PASS / CLOSED | Exact evidence HEAD `8aefde75...` |
| Android instrumentation execution | OPEN — infrastructure blocked | Firebase/Selectel path deferred; not a code failure |

## P1

| Item | Status | Evidence |
|---|---|---|
| Session refresh / revoke | PASS | P1 Evidence `31877362864` |
| Device rotate / revoke | PASS | P1 Evidence `31877362864` |
| Entitlement engine | PASS | P1 Evidence `31877362864` |
| Billing state machine | PASS | P1 Evidence `31877362864` |
| Outbox | PASS | P1 Evidence `31877362864` |
| Worker manager | PASS | P1 Evidence `31877362864` |
| RLS policies | PASS | P1 Evidence `31877362864` |
| SCA / dependency report | PASS | P1 Evidence `31877362864` |
| Performance baseline | PASS | P1 Evidence `31877362864` |
| Reproducible deployment | PASS | Build & Test `31877362872` |
| Production backup/restore smoke | PASS | Build & Test `31877362872`; production-level operation remains outside scope |

The P1 workflow provides aggregate runtime/performance evidence rather than a separate job for every named sub-item; the cited run is nevertheless on the exact evidence HEAD.

## Release certificate / signing

Current release certificate SHA-256:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

The fifth keystore was created atomically because the fourth keystore password could not be safely exported for offline backup. The fifth keystore itself was confirmed by CI and its password was backed up immediately through GPG + Drive + KeePass. No further keystore recreation is planned.

GitHub Secrets in use include `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, and `ANDROID_KEY_PASSWORD`; values are never recorded here.

## Android debug build for owner testing

Latest successful Build & Test run: **31877362872**, exact evidence HEAD `8aefde75cfa000d4688a65631f18c9e75ef51834`.

Artifact: `alpha-0-android-instrumentation-cd9392020a424f5d6c85d17d79701e6b782ae59b` (artifact ID `9245144382`, expires 2026-11-13). It contains `debug/app-debug.apk` and `androidTest/debug/app-debug-androidTest.apk`.

Android application configuration: `applicationId=com.alpha0.app`, `minSdk=29`, `targetSdk=35`, version `1.0.0-RC1`. The manifest declares no runtime permissions; `allowBackup=false`.

On first launch, `MainActivity` invokes `DeviceIdentity`. If the Android Keystore alias `alpha0.device.identity.v1` does not exist, the app automatically creates an EC P-256 key pair in the Android Keystore. No manual registration step or user password is required for this local device-identity bootstrap. The UI reports `DEVICE IDENTITY READY` when initialization succeeds.

## Workflow inventory

### Workflow YAML files present in repository

1. `.github/workflows/build.yml` — **USE / CANONICAL**; Build & Test, release signing/fingerprint, FTL intentionally skipped.
2. `.github/workflows/android-build.yml` — **USE / REVIEW**; separate Android build/test workflow; potential overlap with Build & Test, no deletion performed.
3. `.github/workflows/deploy.yml` — **USE / SEPARATE**; deployment automation.
4. `.github/workflows/p1-evidence.yml` — **USE / SEPARATE**; P1 evidence.
5. `.github/workflows/release.yml` — **USE / SEPARATE**; release automation.
6. `.github/workflows/security.yml` — **USE / SEPARATE**; security checks.

Known GitHub-registered workflows not present in the current repository tree: `ci.yml`, `codeql.yml`, `dependency-review.yml`, `fingerprint-diagnostic.yml`, `full-validation.yml`, `sentinel-backend-ci.yml`, `sentinel-full-validation.yml`, `server-e2e.yml`, and `dynamic/dependabot/update-graph`. These are historical/registered definitions and are not counted as repository workflow files.

## Branch inventory

- `sentinel-ftl-2026-08-13` — **ACTIVE / CANONICAL**.
- `sentinel-1.0.0-rc1-final` — **OPEN PR #19 / current evidence branch**.
- `main` — **BASE / decision point**.
- `sentinel-ftl-repair-2026-08-14` — **TEMPORARY REPAIR / deletion candidate**.
- `p1-close-2026-08-13` — **STALE CANDIDATE**.
- `sentinel-fingerprint-diagnostic` — **STALE CANDIDATE**.
- `sentinel/1.0.0-rc1-gates` — **STALE CANDIDATE**.
- `sentinel-release-hardening-2026-08` — **STALE CANDIDATE**.
- `security/public-release-hardening` — **STALE CANDIDATE**.
- `agent/modernize-alpha0` — **STALE CANDIDATE**.
- `agent/sentinel-complete-platform` — **STALE CANDIDATE**.
- `automation/sentinel-pipeline` — **STALE CANDIDATE**.
- `sentinel/full-stack-builder` — **STALE CANDIDATE**.

No branches were deleted.

## Repository cleanup candidates — review only, no deletion

### Workflow candidates
- `android-build.yml`: review for duplicate Android coverage versus `build.yml`; do not delete until trigger/required-check usage is reviewed.
- Registered-but-absent historical workflows listed above: review/retire only after confirming no required checks depend on them.

### Branch candidates
The stale/temporary branches listed above are candidates for closure after explicit owner approval. No deletion has been performed.

### Files outside active product code
Potential cleanup/review candidates include `update-alpha0.sh`, `update-alpha0-build003a.sh`, and `verify.sh` if they are obsolete one-off migration/build helpers. `docs/AUDIT_CLOSURE_2026-08-13.md` and other dated documentation should be retained until historical evidence is intentionally consolidated; no deletion is recommended merely because it is old.

### Build artifacts committed to git
The current evidence tree contains no committed APK/JAR build outputs; the APKs are CI artifacts, not repository files. No artifact deletion is required.

## Actions history

The 1500+ Actions entries are accumulated historical runs/checks from development, PRs, reruns and debugging, not 1500 active workflow definitions. Run history does not affect builds, signing, secrets or release behavior and does not need cleanup for correctness.

## Owner testing verdict

**VERDICT: ГОТОВ С ОГОВОРКАМИ.**

All declared code/release/security/P1 evidence gates are PASS on the same exact evidence HEAD `8aefde75cfa000d4688a65631f18c9e75ef51834`. Android instrumentation through external CI remains the sole OPEN item and is infrastructure-limited, not a code/signing defect.

**Owner testing readiness: YES.** The debug APK is ready for manual installation and functional testing on an Android device meeting `minSdk 29`. No special registration or production keystore setup is required merely to launch the app; the app bootstraps its device identity automatically in Android Keystore.

## Mandatory operating rule

Whenever exact HEAD, P0/P1 status, or workflow structure changes, update this file in the same commit or immediately in the next commit. Every genuine validation run must record its exact HEAD, workflow/run identifier, result, and P0/P1 impact.
