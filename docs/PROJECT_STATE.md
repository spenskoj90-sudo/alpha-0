# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-20

## Canonical branch

**Canonical branch:** `main`

**Canonical release-validation workflow:** `.github/workflows/build.yml` / **Build & Test**.

## Exact HEAD / validation state

**Current exact HEAD:** `e41d2359144f1f013299a9a1faf5ef463b97ab9e`.

**Current main tree:** `0f676273f47721ab690d146ac479b72535e6cf9f`.

Exact-HEAD GitHub Actions PASS/FAIL status with direct run URLs: **not verified, because the currently available Actions API operation does not return push-triggered workflow runs for this exact main SHA. No run status or URL is recorded here by inference.**

## Current repository facts

### CURRENT / VERIFIED AT THIS MAIN HEAD

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- `app/src/main/java/com/alpha0/app/auth/LoginScreen.kt` exists on `main`.
- `RegisterScreen.kt` is not present in the current main tree.
- PostgreSQL schema exists under `server/migrations/001_initial.sql`.
- Migration order is now represented by `001_initial.sql`, `002_p1_rls.sql`, and `003_user_auth.sql`.
- RLS is enabled on the applicable tables as defined by the current migration set.
- The current canonical branch is `main`.

These repository facts are source-level facts. They are not release acceptance claims without exact-SHA CI/runtime evidence.

## OPEN / NOT ACCEPTED ITEMS

### P0 TCP bug — OPEN

Android client TCP connection failure against the local plaintext test server (`BrokenPipeError`) remains open and requires verification in the client code.

### Documentation state — OPEN

`docs/SENTINEL_CURRENT_STATE.md` and `README.md` still contain statements that require reconciliation with the current main implementation and CI evidence.

### p1-evidence workflow trigger — OPEN

The p1-evidence workflow trigger configuration requires separate verification before any change is made.

### deploy workflow anomaly — OPEN

The discrepancy between the declared `release.published` trigger and historical runs on ordinary pushes requires investigation.

### Repository hygiene — PARTIAL / OPEN

The 16 explicitly audited stale branches are all `ahead_by=0` relative to current `main`, but branch deletion was not completed because the available GitHub connector exposes no branch-delete operation. Registered-but-absent workflow records and duplicate PROJECT_STATE.md files are also subject to cleanup review.

## Workflow inventory

### Workflow files present in the current main tree

- `.github/workflows/android-build.yml`
- `.github/workflows/build.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/p1-evidence.yml`
- `.github/workflows/release.yml`
- `.github/workflows/security.yml`

## Migration inventory

- `server/migrations/001_initial.sql`
- `server/migrations/002_p1_rls.sql`
- `server/migrations/003_user_auth.sql`

The contents of `002_user_auth.sql` were preserved byte-for-byte; only the filename changes to `003_user_auth.sql`.

## Canonical state rules

- `main` is the only canonical product state.
- A branch, PR, local checkout, or historical AI report is not proof of current product state.
- A bare `PASS` is prohibited without exact-SHA evidence.
- Destructive repository cleanup requires direct verification and must not be performed by inference.

## Authority

**Branch-state truth authority:** GPT / Final Integrator.  
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
