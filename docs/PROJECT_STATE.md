# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-23

## Canonical branch

**Canonical branch:** `main`

**Canonical HEAD:** `590623fc5e2d7b31224c1f1dab00119b9aceebdc`
**Tree:** product tree from PR #46 plus subsequent documentation and onboarding changes.

**Latest accepted product change:** PR #51 — battery optimization onboarding.
**Latest accepted documentation change:** PR #54 — post-PR #51 state reconciliation.

## OPEN / NOT ACCEPTED ITEMS

### Postgres/deployment evidence hardening — IN PROGRESS

Branch `test/postgres-deployment-evidence-hardening-2026-08-23` strengthens CI evidence only:
- postgres smoke: device_bindings ACTIVE, active sessions, device:prove ALLOW audit rows, game_events event_id, schema_migrations versions, bind happy-path + revoke SQL;
- deployment-smoke: post-healthz schema readiness via `schema_migrations` and `to_regclass` for sessions/device_bindings (image CMD still runs migrate; no second migrate step, no deploy.yml change).

Production SoR, FTL/GCP, required status checks, manual Android acceptance, and deploy historical anomaly remain OPEN.

### PostgreSQL runtime persistence — OPEN / AUTOMATED EVIDENCE STRENGTHENED

The application selects `PostgresStore(DATABASE_URL)` when `DATABASE_URL` is set, and production startup rejects a missing `DATABASE_URL`. The `/healthz` path also performs `SELECT 1` when the active store is PostgreSQL. Strengthened smoke asserts durable rows and pool recycle. **This does not prove the currently deployed production environment uses PostgreSQL as authoritative SoR.**

### CI governance required checks — OPEN

Live repository metadata documents empty required-check arrays. The owner must configure the intended required status checks/ruleset in GitHub Settings/Rulesets.

### Real-device battery onboarding verification — OPEN MANUAL ACCEPTANCE

PR #51 and product CI establish build/test acceptance. Physical device verification remains required.

### Deploy workflow anomaly — OPEN INVESTIGATION

Current `.github/workflows/deploy.yml` contains only `release: types: [published]`. Do not change the release trigger solely to silence historical runs.

## Authority

**Branch-state truth authority:** GPT / Final Integrator.
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
