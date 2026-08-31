# SENTINEL Observability

**Status:** Active (issue #7)  
**Scope:** Android runtime crash reporting + existing CI failure visibility.

This document describes the two independent observability chains used by SENTINEL.
No real DSN, credentials, or user data appear in this file or in the repository tree.

---

## 1. Runtime errors (Android app) → Sentry

### Purpose
Capture uncaught exceptions and selected runtime errors from the release Android client so that post-crash diagnosis is possible without relying on physical-device log collection alone.

### Data flow
1. `SentinelApplication` (registered in `AndroidManifest.xml`) runs at process start.
2. It reads `BuildConfig.SENTRY_DSN`.
3. If the string is empty (debug builds, PR builds, local developer machines), Sentry is **not** initialized and no network calls are made.
4. If the string is non-empty (release assemble jobs that receive the GitHub secret `SENTRY_DSN`), `SentryAndroid.init` is called with:
   - `isSendDefaultPii = false`
   - screenshots and view hierarchy disabled
   - a `beforeSend` callback that performs data minimization

### Privacy / data minimization (mandatory)
The `beforeSend` scrubber in `SentinelApplication`:

- Clears the Sentry `User` object (id, email, username, IP).
- Removes request headers.
- Strips breadcrumb / extra keys whose names contain: `email`, `token`, `password`, `authorization`, `user`, `session`, `device_id`, `fingerprint`.

Only technical stack traces, device model/SDK version, and non-sensitive breadcrumb messages remain. No PII and no user-authored content is intended to leave the device.

### Configuration sources
| Build type | `SENTRY_DSN` source |
|---|---|
| debug / unit / instrumentation | empty (default) |
| release (CI `assembleRelease`) | GitHub Actions secret `SENTRY_DSN` injected as environment variable |

The DSN value itself is **never** committed. It exists only as a repository secret managed by the Owner.

### Related files
- `app/src/main/java/com/alpha0/app/SentinelApplication.kt`
- `app/build.gradle.kts` (`buildConfigField("SENTRY_DSN", …)`)
- `app/proguard-rules.pro` (Sentry keep rules)
- `.github/workflows/build.yml` and `release-candidate.yml` (env injection for release only)

---

## 2. CI / build failures → GitHub Actions

### Purpose
Surface compile, unit-test, instrumentation, security, and packaging failures for every push and pull request against `main`.

### Existing workflows (authoritative list)
| Workflow file | Name | Trigger |
|---|---|---|
| `.github/workflows/build.yml` | Build & Test | push / PR → main |
| `.github/workflows/security.yml` | Security | (see file) |
| `.github/workflows/android-build.yml` | (Android-specific helper) | (see file) |
| `.github/workflows/p1-evidence.yml` | P1 Evidence | (see file) |
| `.github/workflows/release-candidate.yml` | Release Candidate Artifact | push main / workflow_dispatch |
| `.github/workflows/release.yml` | Release | (see file) |
| `.github/workflows/deploy.yml` | Deploy | (see file) |

These workflows already produce run logs, artifacts, and status checks. No additional Sentry integration is required for CI failures; GitHub Actions remains the single source of truth for build-time errors.

### How to locate a failure
1. Open the PR or the commit on `main`.
2. Inspect the Checks tab / Actions run for the failing job.
3. Download logs or artifacts as needed.
4. Exact evidence claims must include commit SHA + workflow Run ID (see `docs/SENTINEL_EVIDENCE_PROTOCOL.md`).

---

## 3. Separation of concerns

| Concern | Channel | Secret required |
|---|---|---|
| Runtime crash on device | Sentry | `SENTRY_DSN` (release only) |
| CI / packaging / test failure | GitHub Actions | none (logs are public to collaborators) |

Do not send CI failure events into Sentry. Do not embed the DSN in debug builds or documentation.

---

## 4. Operator notes

- Owner must create the GitHub repository secret `SENTRY_DSN` before release builds will emit events.
- After first successful release assemble with a real DSN, verify a synthetic crash appears in the Sentry project dashboard (Owner action only).
- Changing scrubbing rules requires a code change and review; do not relax PII stripping without explicit Owner approval.
