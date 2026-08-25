# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact product HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-25

## Canonical branch

**Canonical branch:** `main`

**Canonical product HEAD:** `bcb9200b9f5e2d7c2fa7ded438e0088e41ca2566`
**Current main documentation commits:** follow the canonical product merge without changing product state.
**Tree:** current main tree after PR #57 merge plus subsequent documentation/evidence/hygiene commits.

**Latest accepted product change:** PR #51 — battery optimization onboarding.
**Latest accepted CI evidence hardening:** PR #57 — PostgreSQL smoke and deployment schema-readiness evidence.

## ACCEPTED / POLICY

### Firebase Test Lab — OPTIONAL / NON-BLOCKING

FTL/GCP authentication is an infrastructure dependency, not a product-correctness gate at the current project stage. Build & Test product jobs remain authoritative for automated CI acceptance; Firebase Test Lab is informational and may fail without blocking product acceptance. Real-device Android acceptance is intentionally deferred and will be performed by the Human Owner as a cumulative device-validation pass after sufficient functionality has accumulated. FTL integration will be restored as a later hardening block.

### Firebase Test Lab — ACCESS RESTORED / EXECUTION CONFIGURED (2026-08-25)

GitHub Actions FTL authentication and Test Lab environment discovery are now operational for project `sentinel-21ca9` using the repository secrets `FIREBASE_SERVICE_ACCOUNT_JSON` and `FIREBASE_GCP_PROJECT_ID`. The Service Account `firebase-adminsdk-fbsvc@sentinel-21ca9.iam.gserviceaccount.com` has the `Firebase Test Lab Admin` role. In Build & Test run `32818319982`, Google authentication passed and `gcloud firebase test android models list` passed. The subsequent instrumentation execution reached the FTL API but was blocked because the Cloud Tool Results API was disabled in the project. Therefore credentials and Test Lab IAM are validated; the remaining infrastructure prerequisite is enabling `toolresults.googleapis.com`. Do not classify this as an APK/product test failure.

### FTL usage-control policy

FTL is a cumulative validation resource and must not be triggered indiscriminately. Test Lab quotas are project-level and shared across instrumentation, Robo, Game Loop, and test matrices. Current documented no-cost limits are 15 test runs/day on Spark (10 virtual + 5 physical). Blaze begins with 60 minutes/day of virtual-device test time and 30 minutes/day of physical-device test time; usage above those limits is billable. Test runs and shards count toward quota, and deflake retries also consume quota. Prefer a single targeted device/matrix for routine regression validation, batch broader device coverage into deliberate acceptance passes, avoid unnecessary reruns, and check current project quota/billing before launching a large matrix. Source: Firebase Test Lab usage/quotas documentation, last updated 2026-08-19.

### PR #57 — ACCEPTED

PR #57 merged as `1b4dc15e82b44de2d3fc65004ed2b113e326433c`. It strengthened PostgreSQL smoke evidence with device/session/audit-specific assertions, bind/revoke SQL proof, schema migration evidence, and added deployment-smoke schema-readiness validation. Exact-head Build & Test product jobs passed; the only failure was the known FTL/GCP authentication exception.

## OPEN / NOT ACCEPTED ITEMS

### PostgreSQL runtime persistence — OPEN / AUTOMATED EVIDENCE STRENGTHENED

The application selects `PostgresStore(DATABASE_URL)` when `DATABASE_URL` is set, and production startup rejects a missing `DATABASE_URL`. The `/healthz` path also performs `SELECT 1` when the active store is PostgreSQL. Strengthened smoke asserts durable rows and pool recycle. **This does not prove the currently deployed production environment uses PostgreSQL as authoritative SoR.**

### CI governance required checks — OPEN

Live repository metadata directly records `protected=true`, `enforcement_level=non_admins`, `contexts=[]`, `checks=[]`. The owner must configure the intended required status checks/ruleset in GitHub Settings/Rulesets.

### Real-device Android acceptance — OPEN / BATCHED MANUAL ACCEPTANCE

Physical-device testing is intentionally accumulated rather than performed after every individual feature. The Human Owner will run one cumulative acceptance pass when the relevant functionality set is sufficiently complete; discovered defects will then be fixed systematically and the acceptance pass repeated.

### Deploy workflow anomaly — OPEN INVESTIGATION

Current `.github/workflows/deploy.yml` contains only `release: types: [published]`. Do not change the release trigger solely to silence historical runs.

### Repository hygiene — OPEN / ACTIVE CLASSIFICATION

The hygiene pass is now active. Current main has 41 branch refs including `main`. Evidence checks against current `main` show `ahead_by=0` for `ui/sentinel-final-design-system-2026-08-23`, `docs/coordination-rules-hygiene-2026-08-22`, `docs/full-state-governance-sync-2026-08-23`, `docs/governance-hygiene-evidence-2026-08-23`, and `docs/reconcile-post-pr51-state-2026-08-23`; these are delete-candidates because they contain no commits unique to the current main lineage. Deletion is not executed in this pass because the available GitHub toolset exposes no branch-delete operation. Other branch refs remain evidence-gated and will not be deleted merely by naming pattern. Ghost workflow records and historical PRs remain separate cleanup categories.

## Authority

**Branch-state truth authority:** GPT / Final Integrator.
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
