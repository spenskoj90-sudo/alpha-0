# SENTINEL Block D — Operational Observability, Performance and Resilience v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Scope

Block D productizes the existing observability/performance/resilience foundations into one bounded operational plane. It does not introduce a production telemetry vendor or production SLO claim.

The implemented repository path is:

`client X-Request-ID → Core normalization → request-scoped server trace id → bounded low-cardinality metrics/recent traces → Companion/voice operational outcomes → admin-only snapshot/OpenMetrics readback → exact-SHA CI failure/performance evidence artifact`

## Core-wide HTTP correlation

Core installs a global HTTP middleware before request handlers execute. The middleware:

- accepts only bounded `X-Request-ID` values matching the public correlation alphabet;
- replaces malformed/missing values with a UUID before downstream handlers inspect headers;
- generates a separate 128-bit server trace id for every HTTP request;
- returns `X-Request-ID` and `X-Sentinel-Trace-ID` response headers;
- records route-template/method/status-class latency without query strings, request bodies, credentials or user/game identifiers.

Request and trace identifiers are intentionally excluded from metric labels. They are retained only in a small bounded recent-trace ring so they cannot create unbounded metric cardinality.

## Operational registry

`BoundedOperationalRegistry` is process-local and provider-neutral. It has explicit caps for:

- metric series;
- per-series latency samples;
- recent trace records.

When the series cap is exhausted, new series are dropped and an overflow counter increments. When the trace ring is full, the oldest trace is evicted and a dropped-trace counter increments. No active series is silently expanded to accommodate attacker-controlled labels.

The registry exposes count, nearest-rank p50/p95 and maximum latency for bounded local samples. Labels are intentionally limited to low-cardinality operational dimensions such as component, route-template/operation and bounded outcome.

## Operator boundary

Operational readback is available only through the existing protected admin control plane:

- `GET /v1/admin/observability` — bounded JSON snapshot including recent trace correlation and capacity counters;
- `GET /v1/admin/metrics` — OpenMetrics-compatible plaintext counters and local latency summaries.

Both routes require the existing `X-Sentinel-Admin-Token` policy and remain subject to existing admin lockout/audit controls. No public unauthenticated metrics endpoint is added.

An external Prometheus/OpenTelemetry/vendor collector is optional environment integration. The repository does not embed a telemetry credential, select a vendor or claim a deployed monitoring backend.

## Companion and voice runtime telemetry

The authenticated loopback Companion WebSocket records fixed operational outcomes for connection/authentication, handshake, heartbeat, passive WoW observation, entitlement revocation and session closure. The labels contain no token, user id, IP address, realm or raw game payload.

The voice HTTP path adds provider/runtime outcomes such as status availability, consent/provider failures, action rejection and accepted STT/TTS presentation flow. Raw audio, transcript and arbitrary synthesis text remain excluded from operational telemetry and existing audit metadata.

The existing heartbeat `HEALTH` envelope remains a separate runtime evidence channel. Launcher RTT evidence still measures only authenticated local loopback WebSocket round trip and is not promoted to Internet/provider/end-to-end latency.

## Client correlation propagation

The repository transports preserve one logical correlation id across the main product surfaces:

- Electron launcher generates `X-Request-ID` in main-process Core session calls; a 401 → refresh → retry chain reuses one id;
- the Next.js secure Core proxy preserves a safe incoming id or generates one and reuses it for refresh/retry; bounded Core correlation response headers are copied back without exposing session cookies/tokens;
- Android `UrlConnectionHttpTransport` supplies a UUID fallback when a caller did not provide `X-Request-ID`, while preserving explicit EventSync correlation/idempotency flow.

Correlation propagation does not alter authentication, entitlement, device proof, idempotency or retry authority.

## Failure-injection evidence

`run_operational_failure_matrix()` is an isolated deterministic harness. It verifies:

1. unsafe correlation input is replaced rather than propagated;
2. metric-series cardinality saturation remains bounded and increments overflow evidence;
3. recent-trace overflow evicts within the configured bound and reports drops;
4. request/trace identifiers never become metric labels.

The harness operates on standalone registries and does not expose a runtime fault-injection endpoint or production chaos toggle.

## CI-local performance evidence

`server/scripts/block_d_evidence.py` performs deterministic local regression measurements for correlation normalization, registry recording and snapshot generation. The Build & Test workflow stores the JSON as an exact-SHA `block-d-operational-evidence-*` artifact and fails if deliberately generous regression budgets are exceeded or the failure matrix fails.

These measurements are **CI-local regression guards, not production SLOs**. They do not claim network, provider, physical-device, database-at-scale, packaged-host or real-game latency. Production SLOs require measured evidence in the selected deployment tied to an exact release commit.

## Existing recovery model

The canonical Companion recovery matrix continues to cover heartbeat timeout, transport failure, peer-auth failure, local kill switch and queue backpressure. `assess_health()` remains fail closed and maps runtime health to `READY`, `DEGRADED`, `AUTH_REQUIRED` or `STOPPED`.

## Evidence classification

After the integrating exact-head CI passes, repository evidence may classify the following as **IMPLEMENTED / INTEGRATION-TESTED**:

- Core-wide HTTP correlation middleware and response propagation;
- bounded operational metric/trace registry;
- admin-only JSON/OpenMetrics readback;
- Companion and voice operational outcome instrumentation;
- launcher/Web/Android correlation propagation;
- deterministic failure-injection harness;
- exact-SHA CI-local performance evidence artifact.

The following remain **ENVIRONMENT-UNVERIFIED / EXTERNAL**:

- deployed Prometheus/OpenTelemetry/vendor backend;
- production alerting/on-call integration;
- production SLOs and real-load benchmark evidence;
- selected production voice/provider network behavior;
- physical-device/packaged-host performance;
- exact WoW/private-server environment acceptance.

Release signing, publication, production secrets and live deployment remain Owner-only gates.
