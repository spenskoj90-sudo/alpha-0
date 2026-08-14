# SENTINEL — PROJECT STATE

Single source of truth for current release-validation work. Update this file whenever exact HEAD, P0/P1 status, or workflow structure changes.

**Last updated:** 2026-08-14

## Canonical branch

**Canonical branch:** `sentinel-ftl-2026-08-13`

Temporary repair branch: `sentinel-ftl-repair-2026-08-14`. It exists only to reconstruct the canonical branch cleanly after an erroneous workflow write; it is not a second development line.

**Canonical release-validation workflow:** `.github/workflows/build.yml` / **Build & Test**.

## Exact HEAD / P0 / P1

**Validation HEAD:** `0809184a94c12ca3621ab25299b47c3c659bc621`.

Its parent is exactly `8daa6545c9d4a4aaf68aa5da0e3a8d5e2e7364fe`. Machine comparison reports exactly one changed file, `.github/workflows/build.yml`, with exactly 2 additions and 2 deletions: only the two expected release-certificate fingerprint literals changed. No reproducible-deployment changes and no deployment gate were carried forward.

**P0:** validation pending. Current release certificate fingerprint: `86:CB:8D:8B:C5:A4:21:28:A3:8A:7A:0C:20:E6:05:25:C6:44:2B:AE:59:6B:FD:33:B0:B7:66:97:9C:72:D2:B4`.

Required canonical chain: decode → keystore format → store password → alias → PrivateKeyEntry → certificate fingerprint → comparison → assembleRelease → apksigner → APK fingerprint → Firebase Test Lab.

**P1:** not revalidated on this exact HEAD; do not infer GREEN from historical evidence.

## Workflow inventory

### Workflow files present in the repository

| Workflow | Role | Disposition |
|---|---|---|
| `.github/workflows/build.yml` | Build & Test; canonical release-validation chain including Android signing/fingerprint and FTL. | **USE / CANONICAL** |
| `.github/workflows/android-build.yml` | Separate Android build/test CI. | **REVIEW / POSSIBLE DUPLICATE**; do not delete without explicit approval. |
| `.github/workflows/deploy.yml` | Deployment automation. | **USE / SEPARATE**; not part of signing validation. |
| `.github/workflows/p1-evidence.yml` | P1 evidence collection. | **USE / SEPARATE** |
| `.github/workflows/release.yml` | Release automation. | **USE / SEPARATE** |
| `.github/workflows/security.yml` | Security checks. | **USE / SEPARATE** |

### Registered in GitHub but absent from the repository tree

GitHub reports 14 registered workflows. Registered-but-absent from the repository tree include:

- `.github/workflows/ci.yml` — `sentinel-ci`
- `.github/workflows/codeql.yml` — `SENTINEL CodeQL`
- `.github/workflows/dependency-review.yml` — `SENTINEL Dependency Review`
- `.github/workflows/fingerprint-diagnostic.yml` — `Fingerprint Diagnostic`
- `.github/workflows/full-validation.yml` — `SENTINEL Full Validation`
- `.github/workflows/sentinel-backend-ci.yml` — `SENTINEL Backend CI`
- `.github/workflows/sentinel-full-validation.yml` — `SENTINEL Full Validation`
- `.github/workflows/server-e2e.yml` — `SENTINEL Server E2E`
- `dynamic/dependabot/update-graph` — `Dependency Graph`

These are not deleted or disabled in this pass.

## Branch inventory

No branch is deleted in this pass.

| Branch | Status / recommendation |
|---|---|
| `sentinel-ftl-2026-08-13` | **ACTIVE / CANONICAL**. Move to the clean repaired HEAD after verification. |
| `sentinel-ftl-repair-2026-08-14` | **TEMPORARY REPAIR**. Candidate for deletion after canonical ref is verified; do not delete automatically. |
| `main` | **BASE / decision point**. Do not advance until release gates are green. |
| `sentinel-1.0.0-rc1-final` | **OPEN PR HEAD**; PR #19 is open and draft. Explicit merge/close decision required. |
| `p1-close-2026-08-13` | **STALE CANDIDATE**. |
| `sentinel-fingerprint-diagnostic` | **STALE CANDIDATE**; temporary diagnostic line. |
| `sentinel/1.0.0-rc1-gates` | **STALE CANDIDATE**. |
| `sentinel-release-hardening-2026-08` | **STALE CANDIDATE**. |
| `security/public-release-hardening` | **STALE CANDIDATE**. |
| `agent/modernize-alpha0` | **STALE CANDIDATE**. |
| `agent/sentinel-complete-platform` | **STALE CANDIDATE**. |
| `automation/sentinel-pipeline` | **STALE CANDIDATE**. |
| `sentinel/full-stack-builder` | **STALE CANDIDATE**. |

## Cleanup candidates — no deletion performed

1. `.github/workflows/android-build.yml` should be compared with the Android portion of `build.yml`; if redundant, propose removal separately.
2. Registered-but-absent workflows, especially `full-validation.yml`, `sentinel-full-validation.yml`, `ci.yml`, and temporary `fingerprint-diagnostic.yml`, should be retired/disabled only after explicit review of their history and triggers.
3. Stale branches above should be closed/deleted only after explicit approval.
4. Historical reports/audits under `docs/` should be consolidated only after a repository-wide file inventory; no blind deletion.
5. Committed APKs, build outputs, logs, or generated artifacts must be identified and proposed for removal if found; none are removed in this pass.

## Release keystore identity

**Current release certificate SHA-256:**

`86:CB:8D:8B:C5:A4:21:28:A3:8A:7A:0C:20:E6:05:25:C6:44:2B:AE:59:6B:FD:33:B0:B7:66:97:9C:72:D2:B4`

**Last recreation:** 2026-08-14, according to the owner's current keystore-recreation report. Passwords and key material are never recorded.

## Mandatory operating rule

Whenever exact HEAD, P0/P1 status, or workflow structure changes, update this file in the same commit or immediately in the next commit. Every genuine validation run must record its exact HEAD, workflow/run identifier, result, and P0/P1 impact.
