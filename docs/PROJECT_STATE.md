# SENTINEL — Project State

> Single source of truth for branch/workflow/validation state. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-14

## 1. Canonical working branch

**Canonical branch:** `sentinel-ftl-2026-08-13`

**Current exact HEAD:** `ef6e99c3e2d04943b6fee99f96c9e959e946e108`

**HEAD commit:** `ci: add non-secret keystore length diagnostic`

**Branch disposition:** this is the active integration/release-validation branch for the current SENTINEL release-validation pass. Do not merge it into `main` yet. The intended next transition is a dedicated PR/merge decision after the release-validation gates are green, including fingerprint extraction/signature verification and the required P0/P1 evidence. No branch is deleted by this state file.

## 2. Canonical release-validation workflow

**Canonical workflow:** `.github/workflows/build.yml` — **Build & Test**.

This is the authoritative release-validation workflow for the current work. Its Android job performs debug build/tests, instrumentation APK creation, release keystore decoding and validation, alias/entry-type checks, release certificate fingerprint extraction/comparison, signed release APK creation, APK signature/fingerprint verification, and instrumentation artifact publication. The workflow also contains repository verification, server core tests/coverage, PostgreSQL integration/recovery, Firebase Test Lab instrumentation, web build, Docker build, deployment smoke, and reproducible-container checks.

### Workflow files present at current canonical HEAD

| File | Role | Current state |
|---|---|---|
| `.github/workflows/android-build.yml` | Legacy/parallel Android CI workflow; Android build/test automation. | Present in HEAD; not the canonical release-validation workflow. |
| `.github/workflows/build.yml` | **Build & Test; canonical release-validation workflow.** | Present in HEAD; authoritative for current release validation. |
| `.github/workflows/deploy.yml` | Deployment-oriented workflow. | Present in HEAD; separate from canonical release validation. |
| `.github/workflows/p1-evidence.yml` | P1 evidence: Python/web/Gradle dependency reports plus P1 runtime/performance tests and artifact upload. | Present in HEAD; evidence workflow, not the canonical release workflow. |
| `.github/workflows/release.yml` | Release workflow for release-oriented automation. | Present in HEAD; separate release workflow. |
| `.github/workflows/security.yml` | Security-oriented CI checks. | Present in HEAD; separate security workflow. |

### Workflows registered in GitHub but absent from current canonical HEAD

GitHub currently reports 14 registered workflows. In addition to the six workflow files above, these registered workflows are not present in `.github/workflows/` at current HEAD:

- `.github/workflows/ci.yml` — `sentinel-ci`
- `.github/workflows/codeql.yml` — `SENTINEL CodeQL`
- `.github/workflows/dependency-review.yml` — `SENTINEL Dependency Review`
- `.github/workflows/fingerprint-diagnostic.yml` — `Fingerprint Diagnostic` (temporary diagnostic branch/workflow; not part of canonical HEAD)
- `.github/workflows/full-validation.yml` — `SENTINEL Full Validation`
- `.github/workflows/sentinel-backend-ci.yml` — `SENTINEL Backend CI`
- `.github/workflows/sentinel-full-validation.yml` — `SENTINEL Full Validation`
- `.github/workflows/server-e2e.yml` — `SENTINEL Server E2E`
- `dynamic/dependabot/update-graph` — `Dependency Graph` (GitHub/Dependabot registered workflow)

**Important:** registered in GitHub does not mean present in the current HEAD. The distinction is intentional and must remain explicit until obsolete workflows are formally retired.

## 3. Last exact validation state / P0-P1

**Last confirmed exact HEAD:** `ef6e99c3e2d04943b6fee99f96c9e959e946e108`.

### P0

- **OPEN — release certificate fingerprint extraction.**
- Root cause is now factually established by the dedicated diagnostic run: `keytool -list -v` emits the SHA256 line as `TAB + SPACE + SHA256:` rather than beginning at column zero.
- Exact observed format: `\t SHA256: <fingerprint>`.
- The current parser in `build.yml` still uses `^SHA256:` and therefore does not match this output. The planned one-line parser fix is to accept leading whitespace before `SHA256:`.
- Password, keystore decoding, alias, and release-key entry-type validation have been confirmed by the diagnostic chain.

### P1

- **NOT RE-VALIDATED on the current exact HEAD in this pass.**
- P1 evidence workflow exists in `.github/workflows/p1-evidence.yml`, but no new P1 evidence run on `ef6e99c3e2d04943b6fee99f96c9e959e946e108` has been established by this state update.
- Therefore P1 must not be marked GREEN merely from historical conversation state. It remains **pending current-HEAD validation**.

### Validation evidence note

The latest diagnostic run against the current keystore produced the expected SHA256 fingerprint and proved the formatting issue. This diagnostic is evidence for the P0 root cause, not a substitute for a successful canonical `Build & Test` release-validation run.

## 4. Branch inventory

No branch is deleted by this inventory update.

| Branch | HEAD | Status |
|---|---|---|
| `sentinel-ftl-2026-08-13` | `ef6e99c3e2d04943b6fee99f96c9e959e946e108` | **ACTIVE / CANONICAL** — current release-validation work. |
| `sentinel-fingerprint-diagnostic` | `49739d2685a5f612a7a56ab409945bc600b782cf` | **STALE / candidate for cleanup later** — temporary diagnostic branch; evidence captured. |
| `main` | `70702f3f992097cea9553c406b5d8febb3a47539` | **BASE / protected decision point** — do not advance until release gates are approved. |
| `p1-close-2026-08-13` | `881cfb98c09a8f4691eeddc59086fab6bb3c0997` | **STALE / candidate for cleanup later** — historical P1 closure branch. |
| `sentinel-1.0.0-rc1-final` | `fb2718e3d10a6bc4c3e44e832c508a6132725887` | **STALE / candidate for cleanup later** — prior RC final branch. |
| `sentinel/1.0.0-rc1-gates` | `001d373ed9b9b9e43019cb158c483587e72f8025` | **STALE / candidate for cleanup later** — prior RC gates work. |
| `sentinel-release-hardening-2026-08` | `e098256c3584a5e43862b66acea3b618e0b69c4e` | **STALE / candidate for cleanup later** — historical release-hardening branch. |
| `security/public-release-hardening` | `e99bd5bc68d840886653dfe49771f1e671a8d106` | **STALE / candidate for cleanup later** — historical security hardening work. |
| `agent/modernize-alpha0` | `e947d24b14b96b6fbb91281acf689db2c4cb4b29` | **STALE / candidate for cleanup later** — separate historical agent branch. |
| `agent/sentinel-complete-platform` | `43896b7dbb0f75d562047937255a6d4f628798ef` | **STALE / candidate for cleanup later** — separate historical platform branch. |
| `automation/sentinel-pipeline` | `8219ddb93857772b604e6b1dfa9cd8c1bf91b254` | **STALE / candidate for cleanup later** — historical automation branch. |
| `sentinel/full-stack-builder` | `1823e0ea42c7bcfc821626f6a566fb43724eeffa` | **STALE / candidate for cleanup later** — historical full-stack branch. |

## 5. Release keystore identity

**Current release certificate SHA-256 fingerprint:**

`60:52:36:AA:B5:EC:83:AC:86:EC:C7:38:FC:7F:18:EF:ED:8E:11:B9:FC:CB:B5:A9:74:59:D6:16:FF:AB:D9:9E`

**Last key/keystore recreation date:** **not established in repository evidence available to this state update; do not infer a date.** The current keystore was successfully decoded and its password, alias, and `PrivateKeyEntry` were confirmed by the diagnostic run on 2026-08-14, but that does not prove when the underlying key was originally/recently created.

Only the fingerprint is recorded here. Passwords and key material are never recorded in this file.

## 6. Update rule

Whenever any of the following changes:

1. exact HEAD;
2. P0/P1 status;
3. workflow structure, canonical workflow selection, or registered-vs-HEAD workflow inventory;
4. release keystore fingerprint;
5. branch disposition;

update `docs/PROJECT_STATE.md` in the **same commit or immediately in the next commit**. Every genuine validation run must update the validation section with its exact HEAD, workflow/run identifier, result, and P0/P1 impact.

This file supplements chat reports; it does not replace them.
