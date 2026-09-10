# SENTINEL Companion Telemetry Fanout v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

The Companion runtime already emits bounded, privacy-safe operational telemetry through `CompanionTelemetrySink`. This increment adds a transport-neutral fanout sink so the same event can reach multiple independent sinks without coupling runtime code to a persistence or telemetry vendor.

## Contract

- At least one sink is required.
- Each event is delivered unchanged to every configured sink, in configuration order.
- The fanout performs no event transformation, authorization, provider calls, or game/action execution.
- Sink failure behavior is intentionally not hidden by this abstraction; callers retain ownership of failure policy.
- Persistence remains an optional sink, allowing local bounded telemetry and PostgreSQL persistence to coexist without changing the event contract.

## Evidence boundary

This establishes the composition seam and unit coverage. It does not claim production telemetry deployment, external provider ingestion, or measured production performance.
