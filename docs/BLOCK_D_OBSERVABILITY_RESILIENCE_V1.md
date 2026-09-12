# SENTINEL Block D — Observability, Performance, Resilience and RC Readiness

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Observability

`CompanionTelemetryEvent.create()` canonicalizes attribute keys and redacts
credential, authorization, cookie, transcript, audio, email and IP fields before
they enter local or persistent sinks. The existing bounded sink retains only a
fixed number of operational events. This is a privacy boundary, not a claim
that every external provider has been audited.

## Measurable budgets

`PerformanceBudget` and `evaluate_budget()` compare a local callable sample to
an explicit operation-scoped millisecond budget. Results are deterministic and
fail closed on operation mismatch. Existing latency statistics retain a bounded
sample window. These measurements do not claim remote, device, network, or
production end-to-end performance.

## Failure/recovery matrix

The canonical matrix covers heartbeat timeout, transport failure, failed peer
authentication, local kill switch, and queue backpressure. Each case names its
expected outcome and explicit recovery action. `assess_health()` maps a runtime
health snapshot to `READY`, `DEGRADED`, `AUTH_REQUIRED`, or `STOPPED`; kill-switch
and authentication failures take precedence over convenience paths.

## Release-candidate boundary

Automated CI remains the evidence source for core, PostgreSQL, web, Android,
security, container reproducibility, and instrumentation gates. Signed release
execution, production secrets/payment credentials, external WoW 3.3.5a/private-
server validation, real-device acceptance, and live deployment remain
Owner-gated. No Block D contract changes that authority boundary.

