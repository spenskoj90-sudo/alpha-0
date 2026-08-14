# SENTINEL — Project State

> Single source of truth for branch/workflow/validation state. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-14

## 1. Canonical working branch

**Canonical branch:** `sentinel-ftl-2026-08-13`

**Current exact HEAD:** `82a6dd452a7079fe5f90d16db1e29d2e182ae400`

**HEAD commit:** `ci: add non-secret release password length diagnostics`

**Branch disposition:** active integration/release-validation branch. Do not merge into `main` yet. After canonical release validation is green, move this work through a dedicated PR/merge decision. Do not delete branches as part of state maintenance.

## 2. Canonical release-validation workflow

**Canonical workflow:** `.github/workflows/build.yml` — **Build & Test**.

It is authoritative for current release validation. The Android job builds/tests debug, builds instrumentation APKs, decodes and validates the release keystore, validates password/alias/entry type, extracts and compares the release certificate fingerprint, assembles the signed release APK, verifies its signature/fingerprint, and uploads instrumentation artifacts. The workflow also runs repository verification, server core tests/coverage, PostgreSQL integration/recovery, Firebase Test Lab instrumentation, web build, Docker build, deployment smoke, and reproducible-container checks.

### Workflow files present in the current HEAD

| File | What it does | Status |
|---|---|---|
| `.github/workflows/android-build.yml` | Android build/test CI. | Present; non-canonical parallel/legacy workflow. |
| `.github/workflows/build.yml` | **Build & Test; canonical release-validation workflow.** | Present; authoritative. |
| `.github/workflows/deploy.yml` | Deployment automation. | Present; separate workflow. |
| `.github/workflows/p1-evidence.yml` | P1 SCA/dependency reports plus runtime/performance evidence and artifacts. | Present; evidence workflow. |
| `.github/workflows/release.yml` | Release-oriented automation. | Present; separate release workflow. |
| `.github/workflows/security.yml` | Security CI checks. | Present; separate security workflow. |

### Registered in GitHub but absent from current HEAD

GitHub currently reports 14 registered workflows. The following registered workflows are not present in the current `.github/workflows/` tree:

- `.github/workflows/ci.yml` — `sentinel-ci`
- `.github/workflows/codeql.yml` — `SENTINEL CodeQL`
- `.github/workflows/dependency-review.yml` — `SENTINEL Dependency Review`
- `.github/workflows/fingerprint-diagnostic.yml` — `Fingerprint Diagnostic` (temporary diagnostic workflow)
- `.github/workflows/full-validation.yml` — `SENTINEL Full Validation`
- `.github/workflows/sentinel-backend-ci.yml` — `SENTINEL Backend CI`
- `.github/workflows/sentinel-full-validation.yml` — `SENTINEL Full Validation`
- `.github/workflows/server-e2e.yml` — `SENTINEL Server E2E`
- `dynamic/dependabot/update-graph` — `Dependency Graph`

Registered in GitHub does not mean present in the current HEAD; both states are recorded deliberately until obsolete workflows are formally retired.

## 3. Exact validation state / P0-P1

**Last confirmed exact HEAD:** `82a6dd452a7079fe5f90d16db1e29d2e182ae400`.

### P0

- **FIX COMMITTED; VALIDATION PENDING.**
- Release certificate extraction parser is fixed and was previously proven against the actual `keytool -v` output: the certificate line contains leading whitespace before `SHA256:`.
- Password, keystore decoding, alias, `PrivateKeyEntry`, certificate extraction, and keystore fingerprint comparison were confirmed by the preceding validation run on `1077801708fe7ff214faf6071d7593050345c1f6`.
- That preceding run still failed at `assembleRelease` with `Get Key failed: Given final block not properly padded`.
- This HEAD adds only non-secret password-length diagnostics immediately before `assembleRelease` to test the store-password/key-password mismatch hypothesis.
- A successful canonical `Build & Test` run on this exact HEAD is still required before P0 can be marked GREEN.

### P1

- **NOT RE-VALIDATED on this exact HEAD.**
- `.github/workflows/p1-evidence.yml` exists and defines the P1 evidence checks, but no new P1 evidence run on `82a6dd452a7079fe5f90d16db1e29d2e182ae400` is recorded here.
- P1 therefore remains **pending current-HEAD validation** and must not be inferred GREEN from historical runs.

### Latest canonical validation evidence

Run `31794533213` on exact HEAD `1077801708fe7ff214faf6071d7593050345c1f6` passed keystore decode, store password, alias, entry type, certificate extraction, and certificate fingerprint comparison, but failed at `assembleRelease` while reading the private key. The new password-length diagnostics have not yet produced CI evidence.

## 4. Branch inventory

No branch is deleted by this state update.

| Branch | Status |
|---|---|
| `sentinel-ftl-2026-08-13` | **ACTIVE / CANONICAL** — current release validation. |
| `sentinel-fingerprint-diagnostic` | **STALE / candidate for cleanup later** — temporary diagnostic branch. |
| `main` | **BASE / merge decision point** — do not advance until release gates are green. |
| `p1-close-2026-08-13` | **STALE / candidate for cleanup later**. |
| `sentinel-1.0.0-rc1-final` | **STALE / candidate for cleanup later**. |
| `sentinel/1.0.0-rc1-gates` | **STALE / candidate for cleanup later**. |
| `sentinel-release-hardening-2026-08` | **STALE / candidate for cleanup later**. |
| `security/public-release-hardening` | **STALE / candidate for cleanup later**. |
| `agent/modernize-alpha0` | **STALE / candidate for cleanup later**. |
| `agent/sentinel-complete-platform` | **STALE / candidate for cleanup later**. |
| `automation/sentinel-pipeline` | **STALE / candidate for cleanup later**. |
| `sentinel/full-stack-builder` | **STALE / candidate for cleanup later**. |

## 5. Release keystore identity

**Current release certificate SHA-256 fingerprint:**

`60:52:36:AA:B5:EC:83:AC:86:EC:C7:38:FC:7F:18:EF:ED:8E:11:B9:FC:CB:B5:A9:74:59:D6:16:FF:AB:D9:9E`

**Last key/keystore recreation date:** **2026-08-13**, supported by the current keystore's `keytool` creation date observed in CI. Passwords and key material are never recorded.

## 6. Mandatory update rule

Whenever exact HEAD, P0/P1 status, workflow structure/canonical workflow, registered-vs-HEAD workflow inventory, release fingerprint, or branch disposition changes, update `docs/PROJECT_STATE.md` in the same commit or immediately in the next commit. Every genuine validation run must record its exact HEAD, workflow/run identifier, result, and P0/P1 impact.

This file supplements chat reports; it does not replace them.
