# SENTINEL Performance Baseline

**Issue:** #10  
**Status:** First CI measurement pass recorded; device/runtime metrics remain UNVERIFIED.  
**Scope:** Alpha-stage build and runtime performance for the Android client, Core API, and web control plane where an existing CI/device execution path already exists.

## 1. Evidence rules

- A performance number is a **measured result** only when it is accompanied by the exact commit SHA, execution context, measurement method, and workflow Run ID or device-test evidence.
- A threshold in this document is a **proposed gate**, not a statement that the current product meets it.
- If a required measurement is not currently emitted by CI or a reproducible device test, record it as **UNVERIFIED** rather than estimating it.
- Do not use PostHog telemetry as the source of CI acceptance evidence. Runtime telemetry may be used later for production trend monitoring when the telemetry contract is available.

## 2. Measurement matrix

| Area | Metric | Measurement method | Context | Proposed threshold | Regression handling |
|---|---|---|---|---|---|
| Build | Android debug build wall-clock time | Run `./gradlew --no-daemon assembleDebug` and capture command elapsed time | GitHub Actions Build & Test Run `34040984006`, synthetic PR-merge execution SHA `9fcb7b6f804560dc68224e00d6c9939f9caad203`, Ubuntu 24.04, JDK 17 | **≤ 5 min** | Investigate sustained breach and distinguish source/build regression from runner variance |
| Build | Core test-suite wall-clock time | Run CI's pytest command and capture command elapsed time | GitHub Actions Build & Test Run `34040984006`, execution SHA `9fcb7b6f804560dc68224e00d6c9939f9caad203`, Python 3.12.14 | **≤ 3 min** excluding dependency installation | Compare repeated exact-SHA runs before treating a single noisy sample as regression |
| Startup | Android cold-start time to first usable screen | Fixed physical/emulated device profile and deterministic UI-ready marker | Device evidence | **≤ 2.0 s** median | **UNVERIFIED** until a repeatable device measurement exists |
| Critical path | Authenticated Core API request latency | Fixed fixture and representative authenticated read path | CI/integration test | **≤ 500 ms p95** for local/integration path | **UNVERIFIED** until an explicit timing measurement is emitted |
| Critical path | Event-batch processing latency | Fixed-size `/v1/events:batch` fixture | Core integration test | **≤ 500 ms p95** | **UNVERIFIED** until timing measurement exists |
| Memory | Android runtime peak memory | Fixed scenario/device using Android tooling | Device test | **≤ 250 MiB** target | **UNVERIFIED** |
| Network | Android request volume | Deterministic authenticated test scenario | Device test | **No unexplained increase > 20%** | **UNVERIFIED** |
| Network | Core event-batch payload size | Fixed fixture at application boundary | CI/integration test | **No unexplained increase > 20%** | **UNVERIFIED** |
| Web | Production build wall-clock time | Run `npm run build` and capture command elapsed time | GitHub Actions Build & Test Run `34040984006`, execution SHA `9fcb7b6f804560dc68224e00d6c9939f9caad203`, Node 20.20.2 | **≤ 5 min** | Compare exact-SHA runs and separate install/setup from build time |

## 3. First measured CI baseline — 2026-09-06

All measurements below are from **Build & Test Run `34040984006`**, which executed the PR #172 merge ref at exact synthetic execution SHA `9fcb7b6f804560dc68224e00d6c9939f9caad203`. This is execution evidence, not a claim that `9fcb7b6f...` is a source commit on `main`.

| Component | Command / phase | Measured result | Evidence |
|---|---|---:|---|
| Android | `./gradlew --no-daemon assembleDebug` | **62 s** | job `101507572386` logs |
| Android | `./gradlew --no-daemon test` | **33 s** | job `101507572386` logs |
| Android | `./gradlew --no-daemon assembleDebugAndroidTest` | **23 s** | job `101507572386` logs |
| Android | `./gradlew --no-daemon assembleRelease` | **3 min 21 s** | job `101507572386` logs |
| Core | `pytest -m 'not postgres' --cov=app --cov-report=term-missing --cov-fail-under=80` | **3.81 s test execution**; 87 passed; 81.30% total coverage | job `101507572300` logs |
| Web | `npm install` | **26 s** | job `101507572341` logs |
| Web | `npm run lint` | **~2.2 s** | job `101507572341` logs |
| Web | `npm run build` | **~8.0 s** | job `101507572341` logs; Next.js production build compiled successfully |

These are baseline observations, not performance guarantees. CI runner region, cache state, dependency cache, hosted runner load and other environment factors affect wall-clock values.

## 4. Establishing the remaining measured baseline

The remaining metrics must establish actual values where an executable CI/device path exists. The result record should contain:

1. exact commit SHA;
2. workflow name and Run ID for CI measurements, or device model/API level/test-run identifier for device measurements;
3. command/test scenario and fixture definition;
4. repetitions and aggregation method (for example median and p95);
5. measured value and unit;
6. whether the value is comparable with the proposed threshold;
7. runner/device context and any known source of variance.

Until this evidence exists, the metric remains **UNVERIFIED**. Proposed thresholds must not be copied into release notes or state documentation as achieved performance.

## 5. Reproducibility requirements

### CI

- Prefer existing GitHub Actions jobs rather than introducing a second performance pipeline.
- Use the same command, runner class, runtime version and fixture when comparing commits.
- Separate dependency installation/setup time from the measured command when the goal is application/build performance.
- Preserve exact SHA and workflow Run ID with every accepted measurement.

### Device tests

- Use one declared device model/API-level profile for the baseline.
- Keep thermal/power state, network mode, app build variant and test fixture consistent enough for comparison.
- Repeat measurements; do not accept a single noisy sample as a regression.
- Device evidence is complementary to CI evidence and must not be represented as CI status.

## 6. Regression policy

A threshold breach is a signal for investigation, not an automatic release blocker until the measurement path is validated and the gate is adopted by the Owner.

For a suspected regression:

1. reproduce the measurement on the same context;
2. compare against the last accepted exact-SHA baseline;
3. identify whether variance comes from runner/device/environment or changed code;
4. record the evidence and root cause in the issue/PR;
5. fix the regression or document an explicit, reviewable threshold change.

No threshold should be silently relaxed to make a failing measurement pass.

## 7. Relationship to release gates

Performance measurements supplement the release gates; they do not replace core tests/coverage, Android build/tests, web lint/build, container build, security/dependency checks, PostgreSQL migration/integration checks or other release evidence.

Performance claims must continue to follow the repository evidence rule: exact commit SHA plus workflow Run ID for CI/test claims. Where that evidence is unavailable, use **UNVERIFIED**.

## 8. Explicit non-goals for Issue #10

- No application/runtime behavior changes.
- No new CI workflow or dependency.
- No production telemetry rollout.
- No credentials or secrets.
- No deployment or release configuration changes.
- No claim that proposed thresholds are currently achieved.
