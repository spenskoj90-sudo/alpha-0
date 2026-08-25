# SENTINEL — Full Audit Reconciliation — 2026-08-25

## Baseline

- Repository: `spenskoj90-sudo/alpha-0`
- Baseline SHA: `209fd63f0bcd0f897ee257cd79d33a12479ccfd9`
- Baseline commit: `fix: correct FTL APK artifact paths`
- Mode: read-only audit reconciliation before implementation changes

## Authority rule

The repository at the exact baseline SHA is the source of truth. AI audit statements are hypotheses until verified against that SHA and, where applicable, exact CI evidence.

## Verified architecture

- Android client: `app/`, Kotlin/Jetpack Compose.
- Backend: `server/`, Python/FastAPI.
- Database: PostgreSQL with SQL migrations under `server/migrations/`.
- Web: Next.js/TypeScript under `web/`.
- CI/CD: GitHub Actions.
- Firebase Test Lab is implemented only in `.github/workflows/build.yml`.

## Grok findings — accepted / rejected

### Accepted

1. FTL is canonical only in `Build & Test`; `ALPHA-0 Android CI` does not contain the FTL job.
2. The APK artifact-path correction at `209fd63` is correct.
3. Build & Test run `32821848970` reached the FTL job `97722118627`.
4. Android, core, PostgreSQL, web, Docker, deployment smoke, and reproducible deployment jobs were successful on that run.
5. FTL authentication, gcloud setup, and model discovery succeeded; the FTL execution failed on GCS object creation permission.
6. The FTL service account requires appropriate object-write permission on the Test Lab results bucket before a valid FTL verification can pass.
7. Process-local rate limiting is a scale limitation, not evidence of an immediate authentication bypass.
8. Android instrumentation coverage is currently narrow and should be expanded deliberately.

### Rejected / corrected

1. There is no duplicate `GET /v1/devices/{device_id}` in `wow_api.py` at this baseline. The router exposes `/v1/devices/me`; the canonical device-id GET is in `server/app/main.py`.
2. `LoginScreen.kt` already executes `AuthApi` work on a background `Thread`; therefore the claim that the login request blocks the Android main thread is not confirmed at this baseline.
3. Android backup is already disabled with `android:allowBackup="false"`.
4. Device registration in `PostgresStore` is already executed inside a database transaction, and `device_bindings.fingerprint_sha256` is globally UNIQUE.
5. Device revoke helper operations use database transactions in the PostgreSQL path.
6. The backend is FastAPI/Python, not Ktor/Kotlin.
7. The current session implementation is opaque random session/refresh tokens hashed in storage, not the hardcoded-JWT-secret architecture described by the conflicting audit.

## DeepSeek findings — accepted / rejected

### Confirmed from repository/context

- FTL GCS permission failure is real and blocks the FTL job.
- Required status-check governance remains unverified through the available GitHub connector and must not be inferred.
- Test coverage needs expansion before broader product growth.
- Android lifecycle/session restoration and network failure handling remain areas for deliberate hardening.

### Not accepted as facts

The following DeepSeek claims are contradicted by the exact baseline repository and are therefore **not implementation tasks** without new evidence:

- hardcoded JWT secret in `server/src/main/resources/application.conf`;
- Ktor backend paths under `server/src/main/kotlin`;
- Room database as the backend persistence mechanism;
- missing `android:allowBackup="false"`;
- missing auth rate limiting;
- missing transaction around PostgreSQL device registration;
- missing Android Keystore instrumentation coverage;
- missing security headers in the FastAPI backend.

## Current blockers

### C1 — FTL GCS IAM

Status: **OPEN / OWNER INFRASTRUCTURE ACTION**.

The exact failed job is Build & Test `32821848970`, job `97722118627`. The failure is `storage.objects.create` denied while uploading the APK to the Firebase Test Lab results bucket. No repository code change can grant this GCP permission.

Required owner action: grant the Firebase/Test-Lab service account the minimum documented bucket/object permission required to create Test Lab objects, then run exactly one Build & Test verification against a current SHA.

Do not add FTL to `android-build.yml` and do not retry blindly before IAM is corrected.

### C2 — Required checks

Status: **OPEN / OWNER GOVERNANCE ACTION**.

The connector does not expose the repository ruleset/branch-protection required-context list. Human owner must verify that the product-critical checks are required on `main`.

### C3 — Policy alignment

Status: **OPEN DECISION**.

FTL currently blocks the Build & Test umbrella job. The repository strategy should explicitly decide whether FTL is a required release gate or an informative/rare regression gate. Do not silently change this policy while the IAM failure is unresolved.

## Preventive backlog

### P0/P1 before major feature expansion

1. Fix and verify FTL GCS IAM.
2. Verify required checks on `main`.
3. Add PostgreSQL security-negative tests for ownership, rotate/revoke, replay, and concurrent operations.
4. Add Android lifecycle/session tests, including process recreation and expired/revoked session behavior.
5. Define and test the refresh-token client flow before increasing authenticated feature count.

### P2 hardening

1. Bound/evict process-local rate-limit state.
2. Evaluate distributed rate limiting before horizontal scaling.
3. Expand FTL instrumentation coverage beyond the current device-identity test.
4. Add web/admin security regression tests.
5. Reconcile future-only database domains with actual product ownership.

## Explicit non-actions

- No release certificate rotation.
- No deletion of `android-build.yml`.
- No blind changes to APK artifact paths.
- No product-code changes based only on the conflicting DeepSeek report.
- No FTL rerun before IAM remediation.
- No destructive branch/PR cleanup.

## Verification target

A future accepted baseline requires:

1. exact SHA recorded;
2. FTL job exists in `Build & Test`;
3. artifact download succeeds;
4. FTL upload proceeds without `storage.objects.create` denial;
5. instrumentation matrix is created and executes;
6. real FTL result JSON is archived;
7. all product jobs remain green;
8. required checks are verified at repository governance level.
