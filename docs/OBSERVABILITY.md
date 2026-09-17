# SENTINEL Observability and Telemetry Contract

**Status:** ACTIVE  
**Machine-readable contract:** `observability/telemetry-contract.v1.json`  
**Scope:** Android runtime error telemetry, provider-neutral Core/Companion operational telemetry, optional staging-only PostHog fanout, exact-SHA CI correlation, privacy/retention, alert policy and GitHub/Linear triage.

No real DSN, API key, credential, user identifier or user-authored payload belongs in this document or repository telemetry configuration.

## 1. Authority and evidence model

Observability is evidence, never authorization. Telemetry cannot grant scopes, entitlement, capability evidence, game-write authority, release readiness or production acceptance.

Four channels remain deliberately separated:

1. **Android runtime crash/error diagnostics → Sentry** when an Owner-managed DSN and complete exact release identity are present.
2. **Core/Companion operational telemetry → bounded local/PostgreSQL observability plane** for low-cardinality runtime health, latency and failure outcomes. This remains the canonical operational plane.
3. **Core/Companion staging operational fanout → optional PostHog HTTPS adapter** only when explicitly configured with `SENTINEL_ENV=staging`, exact release/source identity and an externally injected project key. Network destination is not a free-form URL: `SENTINEL_POSTHOG_REGION` accepts only `us` or `eu`, which map in code to literal PostHog ingestion endpoints. Provider delivery is fail-isolated and disabled by default.
4. **Build/test/security/release failures → GitHub Actions exact-SHA evidence.** CI failures are not mirrored into Sentry/PostHog and runtime telemetry cannot substitute for required checks.

The PostHog implementation is intentionally narrower than a general product analytics SDK. It exports only Companion operational events with a constant non-person distinct ID, disables person-profile processing and applies a fixed low-cardinality attribute allowlist. It is not enabled for production by this contract.

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
| `runtime.operational` | Core/Companion local/PostgreSQL; optional staging PostHog fanout | informational/health | Bounded low-cardinality operational state/outcome |
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

For PostHog staging fanout, `PostHogCompanionTelemetrySink` constructs a new outbound properties object rather than forwarding the local attribute map wholesale. The fixed fields are `distinct_id=sentinel-runtime`, `$process_person_profile=false`, environment, release and exact source SHA; only explicitly allowlisted operational keys such as mode/reason/status/outcome/message or latency class, latency, attempt/backoff and event type may be copied.

The canonical forbidden-dimension set additionally includes email, token, password, authorization, user/user ID, session/session ID, device ID/fingerprint/IP, realm/character, transcript/audio and payload values. Those must never become telemetry labels/dimensions or PostHog properties.

Provider credentials are Owner-managed configuration only. They are not source, documentation, artifact metadata or persisted lineage evidence.

## 5. Environment and network-destination separation

The Android/Sentry runtime allowlist is:

- `development` — explicit non-production development runtime;
- `ci` — explicit synthetic/runtime CI diagnostics if intentionally enabled;
- `staging` — exact-source physical-device acceptance against the canonical staging Core; remote Android/Sentry telemetry remains disabled for the `physicalTest` build even when a DSN is present;
- `release-candidate` — exact-source release candidate evaluation;
- `production` — externally activated production runtime only.

The optional Core/Companion external telemetry network allowlist is separately restricted to `staging`. `configured_posthog_sink()` rejects any other `SENTINEL_ENV`, including `production`.

PostHog egress is also destination-pinned. The runtime accepts only region selector `us` or `eu`; those select literal `https://us.i.posthog.com/capture/` or `https://eu.i.posthog.com/capture/` endpoints embedded in the adapter. Arbitrary URLs, loopback/private-network hosts and credential-bearing URLs are not configurable, preventing the telemetry provider seam from becoming an SSRF primitive.

A build label is not an environment acceptance claim. In particular, producing an Android `release` build does not by itself authorize the `production` environment label.

## 6. Alert policy

Repository policy defines the engineering meaning; actual Sentry/PostHog project alert-rule provisioning is an external/Owner configuration gate.

- **P1 — current-release unhandled fatal:** one or more unhandled fatal events on the currently evaluated exact release identity blocks promotion until triaged or explicitly dispositioned with evidence.
- **P2 — repeated selected runtime error:** the same technical fingerprint repeating on one current release and materially affecting a supported flow requires a tracked defect/reproduction. A numeric provider threshold is intentionally `UNVERIFIED` until measured runtime volume exists; the repository does not invent a statistically meaningless count.
- **Blocking — required CI failure:** any required exact-SHA check failed, missing, stale or pending blocks merge/release readiness. Diagnose and remediate CI; do not create an external telemetry workaround.

Staging PostHog ingestion, if externally activated, is supplementary trend evidence only. Repository acceptance remains based on deterministic tests, exact-SHA CI and explicit runtime/device evidence where required.

## 7. GitHub / Linear triage correlation

Runtime triage follows one deterministic engineering chain:

1. identify provider environment + release + exact source SHA + technical fingerprint;
2. confirm the event is privacy-safe and technically actionable;
3. correlate the source SHA with GitHub commit/workflow/release-evidence state;
4. deduplicate on provider + environment + release + technical fingerprint;
5. link or create one GitHub/Linear defect with the reproduction boundary;
6. fix on a short-lived branch with regression evidence;
7. require exact-PR-HEAD CI and guarded merge;
8. confirm the fixed release identity before closing a runtime regression.

Silence is not proof of a fix. An issue is not auto-closed merely because no additional event arrived.

GitHub Actions remains the source of truth for CI/build failures. Sentry is the runtime source for Android crash/error evidence. Local/PostgreSQL telemetry remains canonical for Core/Companion operational evidence, with optional staging PostHog fanout. Linear/GitHub issue state is workflow metadata, not runtime truth.

## 8. Retention

- Repository/CI artifacts use their workflow retention policies.
- Core recent traces are bounded in memory; optional PostgreSQL telemetry uses the implemented retention seam.
- Sentry account retention is an Owner/external provider setting; repository code limits what can be sent regardless of provider retention.
- PostHog staging account retention is an Owner/external provider setting; the repository adapter controls the minimized payload and fixed destination set but does not claim provider-side retention configuration.

Changing external provider retention cannot weaken the repository privacy boundary.

## 9. Existing activation evidence

Historical activation evidence from 2026-09-06 remains useful only as proof that the Android→Sentry transport worked at that time: Owner observed `SENTINEL_SENTRY_SMOKE` on an Infinix Android 14 release build. Temporary smoke UI/code was removed afterward.

That historical event predates this exact-SHA release-correlation contract and must not be represented as current-release acceptance. Current claims require current release/environment/source identity.

No equivalent claim is made here for live PostHog ingestion. The repository contains a deterministic adapter and tests; actual staging project activation/retention/network evidence remains external until exercised with Owner-managed configuration.

## 10. Related implementation

- `app/src/main/java/com/alpha0/app/SentinelApplication.kt`
- `app/build.gradle.kts`
- `.github/workflows/release-candidate.yml`
- `server/app/core/posthog_telemetry.py`
- `server/app/core/companion_runtime_telemetry.py`
- `observability/telemetry-contract.v1.json`
- `scripts/test_telemetry_contract.py`
- `docs/COMPANION_OBSERVABILITY_V1.md`
- `docs/PROVIDER_SANDBOX_INTEGRATION_V1.md`
- `docs/SENTINEL_EVIDENCE_PROTOCOL.md`

## 11. External and final-stage gates

The repository contract is complete without using production credentials. The following remain external/final-stage evidence:

- Sentry project alert-rule provisioning and account retention settings;
- explicit Android `production` environment activation;
- optional PostHog staging project key/region/account retention and observed ingestion evidence;
- any future decision to permit production PostHog delivery (currently prohibited by code/contract);
- physical-device runtime trend and crash acceptance on the selected release hardware.

Per current release sequencing, physical Android/host/audio/exact-game-environment tests remain final pre-release acceptance rather than blockers for repository-internal completion.
