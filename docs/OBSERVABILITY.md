# SENTINEL Observability and Telemetry Contract

**Status:** ACTIVE  
**Machine-readable contract:** `observability/telemetry-contract.v1.json`  
**Scope:** Android runtime error telemetry, provider-neutral Core/Companion operational telemetry, exact-SHA CI correlation, privacy/retention, alert policy and GitHub/Linear triage.

No real DSN, API key, credential, user identifier or user-authored payload belongs in this document or repository telemetry configuration.

## 1. Authority and evidence model

Observability is evidence, never authorization. Telemetry cannot grant scopes, entitlement, capability evidence, game-write authority, release readiness or production acceptance.

Three channels remain deliberately separate:

1. **Android runtime crash/error diagnostics → Sentry** when an Owner-managed DSN and complete exact release identity are present.
2. **Core/Companion operational telemetry → bounded local/PostgreSQL observability plane** for low-cardinality runtime health, latency and failure outcomes.
3. **Build/test/security/release failures → GitHub Actions exact-SHA evidence.** CI failures are not mirrored into Sentry and runtime telemetry cannot substitute for required checks.

PostHog is mapped in the machine-readable contract but remains disabled. There is no PostHog SDK, credential or external delivery path in the current product. That preserves Local-First / Server-Minimal until an explicit provider activation decision is made.

## 2. Android Sentry release identity

`SentinelApplication` initializes Sentry only when all of these are true:

- `BuildConfig.SENTRY_DSN` is non-empty;
- `BuildConfig.SENTINEL_SOURCE_SHA` is exactly 40 lowercase hexadecimal characters;
- `BuildConfig.SENTINEL_RUNTIME_ENVIRONMENT` is one of `development`, `ci`, `release-candidate`, `production`.

If any condition fails, Sentry remains disabled. There is no fallback to a floating version-only identity.

The emitted Sentry release identity is deterministic:

`com.alpha0.app@<VERSION>+<versionCode>.<sourceSha12>`

The event also carries only two static SENTINEL tags:

- `sentinel.component=android`;
- `sentinel.source_sha=<exact 40-char source SHA>`.

For the Owner-gated signed release-candidate workflow, `GITHUB_SHA` is a valid exact-source fallback because the workflow fails before signing unless `GITHUB_SHA == inputs.source_sha`, then checks out that same SHA. A DSN-bearing GitHub Actions release build defaults to environment `release-candidate`. `production` is never inferred from a normal repository build and requires explicit external activation/configuration.

Debug, PR and ordinary instrumentation builds do not receive the Owner-managed DSN, so they perform no Sentry network delivery even though GitHub may expose a source SHA to the build process.

## 3. Runtime event taxonomy

The minimal external taxonomy is intentionally small:

| Class | Channel | Severity | Meaning |
| --- | --- | --- | --- |
| `runtime.crash.unhandled` | Sentry | P1 | Unhandled fatal on a release-correlated Android runtime |
| `runtime.error.selected` | Sentry | P2 | Explicitly selected technical runtime error suitable for external diagnosis |
| `runtime.operational` | Core/Companion local/PostgreSQL | informational/health | Bounded low-cardinality operational state/outcome |
| `ci.failure` | GitHub Actions | blocking engineering gate | Failed/missing/stale/pending exact-SHA workflow/check evidence |

Do not export game payloads, speech transcripts/audio, character/realm identifiers, auth/session/device identifiers or arbitrary user content merely to enrich diagnostics.

## 4. Privacy and data minimization

Before an Android Sentry event leaves the device, `SentinelApplication.scrubEvent` structurally removes entire potentially user-controlled surfaces rather than depending on a growing key-name denylist:

- `User` object → removed;
- request object, including headers/body/query/cookies → removed;
- breadcrumbs → removed;
- extras → removed;
- screenshot capture → disabled;
- view hierarchy capture → disabled;
- default PII → disabled.

The useful retained context is therefore technical: exception type/stack trace plus the static release, environment, component and exact-source correlation described above.

The canonical forbidden-dimension set additionally includes email, token, password, authorization, user/user ID, session/session ID, device ID/fingerprint/IP, realm/character, transcript/audio and payload values. Those must never become telemetry labels/dimensions.

The DSN is Owner-managed configuration only. It is not source, documentation, artifact metadata or persisted lineage evidence.

## 5. Environment separation

The repository allowlist is:

- `development` — explicit non-production development runtime;
- `ci` — explicit synthetic/runtime CI diagnostics if intentionally enabled;
- `release-candidate` — exact-source release candidate evaluation;
- `production` — externally activated production runtime only.

A build label is not an environment acceptance claim. In particular, producing an Android `release` build does not by itself authorize the `production` environment label.

## 6. Alert policy

Repository policy defines the engineering meaning; actual Sentry project alert-rule provisioning is an external/Owner configuration gate.

- **P1 — current-release unhandled fatal:** one or more unhandled fatal events on the currently evaluated exact release identity blocks promotion until triaged or explicitly dispositioned with evidence.
- **P2 — repeated selected runtime error:** the same technical fingerprint repeating on one current release and materially affecting a supported flow requires a tracked defect/reproduction. A numeric provider threshold is intentionally `UNVERIFIED` until measured runtime volume exists; the repository does not invent a statistically meaningless count.
- **Blocking — required CI failure:** any required exact-SHA check failed, missing, stale or pending blocks merge/release readiness. Diagnose and remediate CI; do not create a Sentry workaround.

## 7. GitHub / Linear triage correlation

Runtime triage follows one deterministic engineering chain:

1. identify Sentry environment + release + exact source SHA + technical fingerprint;
2. confirm the event is privacy-safe and technically actionable;
3. correlate the source SHA with GitHub commit/workflow/release-evidence state;
4. deduplicate on provider + environment + release + technical fingerprint;
5. link or create one GitHub/Linear defect with the reproduction boundary;
6. fix on a short-lived branch with regression evidence;
7. require exact-PR-HEAD CI and guarded merge;
8. confirm the fixed release identity before closing a runtime regression.

Silence is not proof of a fix. An issue is not auto-closed merely because no additional event arrived.

GitHub Actions remains the source of truth for CI/build failures. Sentry is the runtime source for Android crash/error evidence. Linear/GitHub issue state is workflow metadata, not runtime truth.

## 8. Retention

- Repository/CI artifacts use their workflow retention policies.
- Core recent traces are bounded in memory; optional PostgreSQL telemetry uses the implemented retention seam.
- Sentry account retention is an Owner/external provider setting; repository code limits what can be sent regardless of provider retention.
- PostHog retention is not applicable because PostHog delivery is disabled.

Changing external provider retention cannot weaken the repository privacy boundary.

## 9. Existing activation evidence

Historical activation evidence from 2026-09-06 remains useful only as proof that the Android→Sentry transport worked at that time: Owner observed `SENTINEL_SENTRY_SMOKE` on an Infinix Android 14 release build. Temporary smoke UI/code was removed afterward.

That historical event predates this exact-SHA release-correlation contract and must not be represented as current-release acceptance. Current claims require current release/environment/source identity.

## 10. Related implementation

- `app/src/main/java/com/alpha0/app/SentinelApplication.kt`
- `app/build.gradle.kts`
- `.github/workflows/release-candidate.yml`
- `observability/telemetry-contract.v1.json`
- `scripts/test_telemetry_contract.py`
- `docs/COMPANION_OBSERVABILITY_V1.md`
- `docs/SENTINEL_EVIDENCE_PROTOCOL.md`

## 11. External and final-stage gates

The repository contract is complete without using production credentials. The following remain external/final-stage evidence:

- Sentry project alert-rule provisioning and account retention settings;
- explicit `production` environment activation;
- any future PostHog provider selection/credential/network path;
- physical-device runtime trend and crash acceptance on the selected release hardware.

Per current release sequencing, physical Android/host/audio/exact-game-environment tests remain final pre-release acceptance rather than blockers for repository-internal completion.
