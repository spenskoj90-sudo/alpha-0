# Companion Observability v1

## Status

Runtime and persistent Companion observability seams are implemented. External provider delivery remains optional, disabled by default and staging-only.

## Contract

`server/app/core/companion_observability.py` defines a provider-neutral `CompanionTelemetrySink` and a bounded, thread-safe local sink. `CompanionRuntime` can emit operational events without depending on a telemetry vendor.

`server/app/core/companion_persistent_observability.py` defines `PostgresCompanionTelemetrySink`, which persists the same bounded event contract to PostgreSQL and exposes explicit expiry cleanup. Persistence is provider-neutral and does not perform external provider calls.

`server/app/core/posthog_telemetry.py` implements an optional HTTPS PostHog sink for pre-release staging only. It is disabled unless explicitly configured, requires `SENTINEL_ENV=staging` plus exact release/source correlation, sends a constant non-person distinct ID with person-profile processing disabled, and copies only a fixed low-cardinality operational attribute allowlist. Provider failures are swallowed into a bounded dropped-event counter so local runtime and PostgreSQL observability remain authoritative.

Current event namespace includes:

- `companion.runtime.started`
- `companion.runtime.heartbeat`
- `companion.runtime.latency`
- `companion.runtime.degraded`
- `companion.runtime.reconnect`
- `companion.runtime.stopped`
- `companion.runtime.kill_switch`
- bounded transport/adapter events under the existing `companion.*` namespace.

Events carry only operational metadata such as mode, reason, attempt count, backoff delay, message/latency class and measured latency. Raw game payloads, chat content and user identifiers are not part of the external event contract.

## Persistence and retention

Migration `005_companion_telemetry.sql` creates a dedicated telemetry table with namespace validation, timezone-aware timestamps, deterministic JSONB attributes, expiry timestamps and indexes for retention cleanup and event-time queries. The persistent sink requires a positive retention interval and stores `expires_at = observed_at + retention`. `purge_expired()` removes rows whose retention window has elapsed.

PostHog account retention is not controlled by repository code and remains an external staging configuration gate. The repository controls only the minimized event envelope that may be sent.

## Safety and resource bounds

The local sink is bounded and evicts the oldest event when capacity is reached. Event attributes are normalized into deterministic sorted tuples. Timestamps must be timezone-aware. The persistent sink serializes only those bounded attributes and performs no provider or game-process I/O.

The PostHog sink accepts only its explicit allowlist and drops user/device/session/game/request identity dimensions even when a local telemetry event contains them. Its delivery failures cannot interrupt Core/Companion execution.

The telemetry sinks are observational only: they cannot authorize commands, execute actions, manipulate game processes or bypass the Policy Engine / Action Gateway.

## Scope boundary

This increment establishes bounded local/PostgreSQL telemetry plus an optional staging-only PostHog delivery seam. It does not claim production PostHog activation, provider-account retention/alert configuration, production deployment or real-device latency evidence. Those remain separate acceptance gates.
