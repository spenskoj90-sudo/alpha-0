# SENTINEL — Project State

> Single source of truth for branch/workflow/validation state. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-14

## 1. Canonical working branch

**Canonical branch:** `sentinel-ftl-2026-08-13`

**Current exact HEAD:** `9227b96aa50e4cd665c9ca09dc55c6c5db99cc20`

**HEAD commit:** `fix: accept keytool SHA256 leading whitespace`

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

**Last confirmed exact HEAD:** `9227b96aa50e4cd665c9ca09dc55c6c5db99cc20`.

### P0

- **FIX COMMITTED; VALIDATION PENDING.**
- Root cause was established by diagnostic run `31793907706`: `keytool -list -v` emits the certificate line as `TAB + SPACE + SHA256: <fingerprint>`.
- The parser fix in this HEAD changes the match from `^SHA256:` to `^[[:space:]]*SHA256:`.
- Password, keystore decoding, alias, and `PrivateKeyEntry` validation were confirmed by the diagnostic chain.
- A successful canonical `Build & Test` run on this exact HEAD is still required before P0 can be marked GREEN.

### P1

- **NOT RE-VALIDATED on this exact HEAD.**
- `.github/workflows/p1-evidence.yml` exists and defines the P1 evidence checks, but no new P1 evidence run on `9227b96aa50e4cd665c9ca09dc55c6c5db99cc20` is recorded here.
- P1 therefore remains **pending current-HEAD validation** and must not be inferred GREEN from historical runs.

### Latest diagnostic evidence

The diagnostic run produced the expected fingerprint and established the formatting defect. It was root-cause evidence, not release-validation evidence.

## 4. Branch inventory

No branch is deleted by this state update.

| Branch | HEAD | Status |
|---|---|---|
| `sentinel-ftl-2026-08-13` | `9227b96aa50e4cd665c9ca09dc55c6c5db99cc20` | **ACTIVE / CANONICAL** — current release validation. |
| `sentinel-fingerprint-diagnostic` | `49739d2685a5f612a7a56ab409945bc600b782cf` | **STALE / candidate for cleanup later** — temporary diagnostic branch. |
| `main` | `70702f3f992097cea9553c406b5d8febb3a47539` | **BASE / merge decision point** — do not advance until release gates are green. |
| `p1-close-2026-08-13` | `881cfb98c09a8f4691eeddc59086fab6bb3c0997` | **STALE / candidate for cleanup later**. |
| `sentinel-1.0.0-rc1-final` | `fb2718e3d10a6bc4c3e44e832c508a6132725887` | **STALE / candidate for cleanup later**. |
| `sentinel/1.0.0-rc1-gates` | `001d373ed9b9b9e43019cb158c483587e72f8025` | **STALE / candidate for cleanup later**. |
| `sentinel-release-hardening-2026-08` | `e098256c3584a5e43862b66acea3b618e0b69c4e` | **STALE / candidate for cleanup later**. |
| `security/public-release-hardening` | `e99bd5bc68d840886653dfe49771f1e671a8d106` | **STALE / candidate for cleanup later**. |
| `agent/modernize-alpha0` | `e947d24b14b96b6fbb91281acf689db2c4cb4b29` | **STALE / candidate for cleanup later**. |
| `agent/sentinel-complete-platform` | `43896b7dbb0f75d562047937255a6d4f628798ef` | **STALE / candidate for cleanup later**. |
| `automation/sentinel-pipeline` | `8219ddb93857772b604e6b1dfa9cd8c1bf91b254` | **STALE / candidate for cleanup later**. |
| `sentinel/full-stack-builder` | `1823e0ea42c7bcfc821626f6a566fb43724eeffa` | **STALE / candidate for cleanup later**. |

## 5. Release keystore identity

**Current release certificate SHA-256 fingerprint:**

`60:52:36:AA:B5:EC:83:AC:86:EC:C7:38:FC:7F:18:EF:ED:8E:11:B9:FC:CB:B5:A9:74:59:D6:16:FF:AB:D9:9E`

**Last key/keystore recreation date:** **not established by repository evidence; do not infer a date.** The current keystore was decoded and its password, alias, and `PrivateKeyEntry` were confirmed on 2026-08-14, but that does not prove when the underlying key was created/recreated.

Only the fingerprint is recorded here. Passwords and key material are never recorded.

## 6. Mandatory update rule

Whenever exact HEAD, P0/P1 status, workflow structure/canonical workflow, registered-vs-HEAD workflow inventory, release fingerprint, or branch disposition changes, update `docs/PROJECT_STATE.md` in the same commit or immediately in the next commit. Every genuine validation run must record its exact HEAD, workflow/run identifier, result, and P0/P1 impact.

This file supplements chat reports; it does not replace them.
