# SENTINEL Performance Baseline

**Issue:** #10  
**Status:** Proposed measurement contract; no numeric performance result is claimed by this document.  
**Scope:** Alpha-stage build and runtime performance for the Android client, Core API, and web control plane where an existing CI/device execution path already exists.

## 1. Evidence rules

- A performance number is a **measured result** only when it is accompanied by the exact commit SHA, execution context, measurement method, and workflow Run ID or device-test evidence.
- A threshold in this document is a **proposed gate**, not a statement that the current product meets it.
- If a required measurement is not currently emitted by CI or a reproducible device test, record it as **UNVERIFIED** rather than estimating it.
- Do not use PostHog telemetry as the source of CI acceptance evidence. Runtime telemetry may be used later for production trend monitoring when the telemetry contract is available.

## 2. Measurement matrix

| Area | Metric | Measurement method | Context | Proposed threshold | Regression handling |
|---|---|---|---|---|---|
| Build | Android debug build wall-clock time | Run `./gradlew --no-daemon assembleDebug` with a clean checkout; capture elapsed wall-clock time | GitHub Actions Android build/tests job on `ubuntu-latest`, JDK 17 | **≤ 5 min** for the full command; validate against repeated runs before treating as stable | Investigate any run > threshold and confirm whether the change is source/build related or runner variance; do not waive repeatedly without recorded rationale |
| Build | Core test-suite wall-clock time | Run the existing core test command used by CI and capture elapsed wall-clock time | GitHub Actions Core tests and coverage job, Python 3.12 | **≤ 3 min** excluding dependency installation | Compare with recent exact-SHA evidence; investigate sustained or material regression rather than one noisy runner sample |
| Startup | Android cold-start time to first usable screen | On a fixed physical/emulated device profile, force-stop/clear app state as defined by the test, launch the debug APK, and measure from launch request to the first deterministic UI-ready marker | Device/instrumentation test; same device profile for comparison | **≤ 2.0 s** median over a documented repeated sample | Treat threshold breach as a performance regression only after repeating on the same device profile and confirming the marker is deterministic |
| Critical path | Authenticated Core API request latency | Exercise a representative authenticated read path with a fixed test fixture and measure client-observed latency; use the same endpoint/fixture for comparison | CI integration test against the repository's PostgreSQL test service or a fixed test environment | **≤ 500 ms p95** for the selected local/integration path; production latency is not inferred from this value | Compare p95 on repeated exact-SHA runs; investigate application/database changes separately from runner/network noise |
| Critical path | Event-batch processing latency | Submit a fixed-size representative `/v1/events:batch` fixture and measure request completion time | Core integration test with deterministic fixture | **≤ 500 ms p95** for the CI integration context | Re-run with the same fixture; inspect projection/database work before attributing the change to general runtime performance |
| Memory | Android runtime peak memory | Capture peak process memory for the same startup + representative interaction scenario using Android device tooling; keep device/API level fixed | Device test; fixed device profile | **≤ 250 MiB** peak RSS/PSS target for the documented scenario | Repeat before filing a regression; compare like-for-like device/API level and scenario |
| Network | Android request volume for representative authenticated flow | Capture HTTP request count/bytes for a fixed scenario using test instrumentation or an approved test proxy; do not collect real user traffic | Device test with deterministic fixture and no production credentials | **No unexplained increase > 20%** versus the established baseline | Identify the request responsible and require an explicit rationale for intentional increases |
| Network | Core API payload size for representative event batch | Measure serialized request/response bytes for a fixed fixture at the application boundary | CI/integration test with deterministic fixture | **No unexplained increase > 20%** versus the established baseline | Compare the same fixture and encoding; investigate schema/payload changes |
| Web | Production build wall-clock time | Run the existing production build command from the web workspace and capture elapsed wall-clock time | GitHub Actions web build job on the repository's configured runner | **≤ 5 min** for the build command; establish actual baseline before tightening | Compare exact-SHA runs and distinguish dependency-install time from build execution time where logs permit |

## 3. Establishing the first measured baseline

The first measurement pass must establish the actual value for each metric that has an executable CI/device path. The result record should contain:

1. exact commit SHA;
2. workflow name and Run ID for CI measurements, or device model/API level/test-run identifier for device measurements;
3. command/test scenario and fixture definition;
4. repetitions and aggregation method (for example median and p95);
5. measured value and unit;
6. whether the value is comparable with the proposed threshold;
7. runner/device context and any known source of variance.

Until this evidence exists, the metric remains **UNVERIFIED**. The proposed thresholds above must not be copied into release notes or state documentation as achieved performance.

## 4. Reproducibility requirements

### CI

- Prefer the existing GitHub Actions jobs rather than introducing a second performance pipeline for this documentation-only issue.
- Use the same command, runner class, runtime version, and fixture when comparing commits.
- Separate dependency installation/setup time from the measured command when the goal is application/build performance.
- Preserve the exact SHA and workflow Run ID with every accepted measurement.

The current repository CI includes dedicated Android build/tests, Core tests/coverage, PostgreSQL integration/recovery, and web build gates. The release policy separately requires the corresponding automated release evidence.

### Device tests

- Use one declared device model/API-level profile for the baseline.
- Keep thermal/power state, network mode, app build variant, and test fixture consistent enough for comparison.
- Repeat measurements; do not accept a single noisy sample as a regression.
- Device evidence is complementary to CI evidence and must not be represented as CI status.

## 5. Regression policy

A threshold breach is a signal for investigation, not an automatic release blocker until the measurement path is validated and the gate is adopted by the Owner.

For a suspected regression:

1. reproduce the measurement on the same context;
2. compare against the last accepted exact-SHA baseline;
3. identify whether variance comes from the runner/device/environment or the changed code;
4. record the evidence and root cause in the issue/PR;
5. either fix the regression or document an explicit, reviewable threshold change.

No threshold should be silently relaxed to make a failing measurement pass.

## 6. Relationship to release gates

The release gate policy already requires core tests and coverage, Android build/tests, web lint/build, container build, security/dependency checks, PostgreSQL migration/integration checks, and other release evidence. Performance measurements in this document supplement those gates; they do not replace them.

Performance claims must continue to follow the repository evidence rule: exact commit SHA plus workflow Run ID for CI/test claims. Where that evidence is unavailable, use **UNVERIFIED**.

## 7. Explicit non-goals for Issue #10

- No application/runtime behavior changes.
- No new CI workflow or dependency.
- No production telemetry rollout.
- No credentials or secrets.
- No deployment or release configuration changes.
- No claim that the proposed thresholds are currently achieved.
