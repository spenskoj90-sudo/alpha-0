# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-23

## Canonical branch

**Canonical branch:** `main`

**Canonical HEAD:** `064e02053346b155f99f2637f4daf008a7fd5a90`
**Tree:** product tree after PR #57 merge, with PostgreSQL/deployment evidence hardening accepted and FTL policy formalized.

**Latest accepted product change:** PR #51 — battery optimization onboarding.
**Latest accepted CI evidence hardening:** PR #57 — PostgreSQL smoke and deployment schema-readiness evidence.

## ACCEPTED / POLICY

### Firebase Test Lab — OPTIONAL / NON-BLOCKING

FTL/GCP authentication is an infrastructure dependency, not a product-correctness gate at the current project stage. Build & Test product jobs remain authoritative for automated CI acceptance; Firebase Test Lab is informational and may fail without blocking product acceptance. Real-device Android acceptance is intentionally deferred and will be performed by the Human Owner as a cumulative device-validation pass after sufficient functionality has accumulated. FTL integration will be restored as a later hardening block.

### PR #57 — ACCEPTED

PR #57 merged as `1b4dc15e82b44de2d3fc65004ed2b113e326433c`. It strengthened PostgreSQL smoke evidence with device/session/audit-specific assertions, bind/revoke SQL proof, schema migration evidence, and added deployment-smoke schema-readiness validation. Exact-head Build & Test product jobs passed; the only failure was the known FTL/GCP authentication exception.

## OPEN / NOT ACCEPTED ITEMS

### PostgreSQL runtime persistence — OPEN / AUTOMATED EVIDENCE STRENGTHENED

The application selects `PostgresStore(DATABASE_URL)` when `DATABASE_URL` is set, and production startup rejects a missing `DATABASE_URL`. The `/healthz` path also performs `SELECT 1` when the active store is PostgreSQL. Strengthened smoke asserts durable rows and pool recycle. **This does not prove the currently deployed production environment uses PostgreSQL as authoritative SoR.**

### CI governance required checks — OPEN

Live repository metadata documents empty required-check arrays. The owner must configure the intended required status checks/ruleset in GitHub Settings/Rulesets.

### Real-device Android acceptance — OPEN / BATCHED MANUAL ACCEPTANCE

Physical-device testing is intentionally accumulated rather than performed after every individual feature. The Human Owner will run one cumulative acceptance pass when the relevant functionality set is sufficiently complete; discovered defects will then be fixed systematically and the acceptance pass repeated.

### Deploy workflow anomaly — OPEN INVESTIGATION

Current `.github/workflows/deploy.yml` contains only `release: types: [published]`. Do not change the release trigger solely to silence historical runs.

### Repository hygiene — OPEN / DEFERRED

Repository cleanup remains intentionally deferred until the working-core acceptance state is stable. Destructive cleanup remains evidence-gated.

## Authority

**Branch-state truth authority:** GPT / Final Integrator.
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
