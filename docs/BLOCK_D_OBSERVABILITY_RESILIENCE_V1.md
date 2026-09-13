# SENTINEL Block D — Observability, Performance, Resilience and RC Readiness

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Observability

`CompanionTelemetryEvent.create()` canonicalizes attribute keys and redacts credential, authorization, cookie, transcript, audio, email and IP fields before they enter local or persistent sinks. The bounded sink retains only a fixed number of operational events. This is a privacy boundary, not a claim that every external provider has been audited.

The authenticated loopback Companion path also carries a bounded runtime-health correlation. Every launcher heartbeat has an opaque UUID. Core records that heartbeat into the live `CompanionRuntime`, returns a `HEALTH` envelope correlated to the exact heartbeat UUID and exposes only allowlisted runtime counters plus an opaque per-connection UUID. The response deliberately excludes peer identity, IP addresses, tokens and account/game payloads.

The launcher accepts runtime HEALTH only when it matches one of at most eight pending heartbeat UUIDs. It measures local loopback round-trip time with its own monotonic execution clock, retains at most 64 samples and computes count/min/max/average/nearest-rank-p95. The worker and Electron parent independently allowlist the health object before the read-only overlay may display p95 RTT. This path is operational evidence only; it is not an authorization or action channel.

## Measurable budgets

`PerformanceBudget` and `evaluate_budget()` compare a local callable sample to an explicit operation-scoped millisecond budget. Results are deterministic and fail closed on operation mismatch. Existing Core latency statistics and launcher loopback RTT statistics retain bounded sample windows.

The launcher RTT evidence measures only the authenticated local Companion WebSocket round trip on the running host. It does **not** claim Internet, provider, physical-device, production ingress or end-to-end game latency. Production SLOs require measurements tied to the actual selected runtime and exact release commit.

## Failure/recovery matrix

The canonical matrix covers heartbeat timeout, transport failure, failed peer authentication, local kill switch and queue backpressure. Each case names its expected outcome and explicit recovery action. `assess_health()` maps a runtime health snapshot to `READY`, `DEGRADED`, `AUTH_REQUIRED`, or `STOPPED`; kill-switch and authentication failures take precedence over convenience paths.

Runtime-health correlation is fail closed: malformed health payloads, unknown heartbeat UUIDs, stale/replayed acknowledgements, negative RTT values and RTT values above the bounded 60-second evidence range are rejected rather than incorporated into statistics. Pending correlation state is cleared on reconnect/stop so one connection cannot satisfy another connection's heartbeat evidence.

## Remaining Block D scope

This increment makes Companion heartbeat liveness and local RTT operational rather than serializer-only. Block D remains incomplete until the remaining applicable runtime evidence is implemented or explicitly scoped out with evidence. In particular, Core-wide HTTP request/correlation propagation, deployed metrics/tracing composition, broader benchmark/failure-injection measurements and addon/launcher telemetry beyond this Companion link remain separate targets where absent.

No external Prometheus/OpenTelemetry/vendor service is implied by the internal bounded metrics path.

## Release-candidate boundary

Automated CI remains the evidence source for core, PostgreSQL, web, Android, launcher, security, container reproducibility and instrumentation gates. Signed release execution, production secrets/payment credentials, external WoW 3.3.5a/private-server validation, real-device/packaged-host acceptance and live deployment remain Owner-gated. No Block D contract changes that authority boundary.
