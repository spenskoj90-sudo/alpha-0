# Companion Observability v1

## Status

Runtime and persistent Companion observability seams are implemented. External provider delivery remains optional and separate.

## Contract

`server/app/core/companion_observability.py` defines a provider-neutral `CompanionTelemetrySink` and a bounded, thread-safe local sink. `CompanionRuntime` can emit operational events without depending on a telemetry vendor.

`server/app/core/companion_persistent_observability.py` defines `PostgresCompanionTelemetrySink`, which persists the same bounded event contract to PostgreSQL and exposes explicit expiry cleanup. Persistence is provider-neutral and does not perform external provider calls.

Current event namespace:

- `companion.runtime.started`
- `companion.runtime.heartbeat`
- `companion.runtime.latency`
- `companion.runtime.degraded`
- `companion.runtime.reconnect`
- `companion.runtime.stopped`
- `companion.runtime.kill_switch`

Events carry only operational metadata such as mode, reason, attempt count, backoff delay and measured latency. Raw game payloads, chat content and user identifiers are not part of the event contract.

## Persistence and retention

Migration `005_companion_telemetry.sql` creates a dedicated telemetry table with namespace validation, timezone-aware timestamps, deterministic JSONB attributes, expiry timestamps and indexes for retention cleanup and event-time queries. The persistent sink requires a positive retention interval and stores `expires_at = observed_at + retention`. `purge_expired()` removes rows whose retention window has elapsed.

## Safety and resource bounds

The local sink is bounded and evicts the oldest event when capacity is reached. Event attributes are normalized into deterministic sorted tuples. Timestamps must be timezone-aware. The persistent sink serializes only those bounded attributes and performs no provider or game-process I/O.

The telemetry sinks are observational only: they cannot authorize commands, execute actions, manipulate game processes or bypass the Policy Engine / Action Gateway.

## Scope boundary

This increment establishes persistent local/PostgreSQL telemetry storage and retention behavior. It does not claim PostHog ingestion, production deployment, real-device latency evidence, or external-provider delivery. Those remain separate acceptance gates.
