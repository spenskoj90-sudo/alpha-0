# Companion Observability v1

## Status

Runtime observability seam implemented. Persistent/provider-backed delivery remains open.

## Contract

`server/app/core/companion_observability.py` defines a provider-neutral `CompanionTelemetrySink` and a bounded, thread-safe local sink. `CompanionRuntime` can emit operational events without depending on a telemetry vendor.

Current event namespace:

- `companion.runtime.started`
- `companion.runtime.heartbeat`
- `companion.runtime.latency`
- `companion.runtime.degraded`
- `companion.runtime.reconnect`
- `companion.runtime.stopped`
- `companion.runtime.kill_switch`

Events carry only operational metadata such as mode, reason, attempt count, backoff delay and measured latency. Raw game payloads, chat content and user identifiers are not part of the event contract.

## Safety and resource bounds

The local sink is bounded and evicts the oldest event when capacity is reached. Event attributes are normalized into deterministic sorted tuples. Timestamps must be timezone-aware. The runtime performs no network I/O through this seam.

The telemetry sink is observational only: it cannot authorize commands, execute actions, manipulate game processes or bypass the Policy Engine / Action Gateway.

## Remaining work

A persistent sink and optional external provider adapter still require a separate implementation, with retention/privacy enforcement and acceptance evidence. This seam is therefore not evidence of production telemetry delivery or PostHog ingestion.
