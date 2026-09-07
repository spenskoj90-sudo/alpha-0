# SENTINEL — Companion Runtime v1

**Status:** ACTIVE FOUNDATION  
**Version:** 1.0

## Purpose

This runtime layer owns Companion lifecycle safety around the transport-neutral protocol. It tracks active/degraded/stopped state, heartbeat freshness, reconnect backoff and measured message latency. It does not authorize or execute game actions.

## Lifecycle

- `ACTIVE` — recent heartbeat observed within the configured timeout.
- `DEGRADED` — heartbeat freshness has expired; the runtime must not pretend the connection is healthy.
- `STOPPED` — explicitly stopped or not started; watchdog cannot revive it.
- A new `start()` establishes a fresh active runtime session.

## Freshness

The default heartbeat timeout is 10 seconds. The timeout is configurable but must be positive. Heartbeat timestamps must be timezone-aware and monotonic. A heartbeat exactly at the timeout boundary is still considered fresh; expiry occurs strictly after the configured interval.

## Reconnect backoff

Reconnect delay starts at the configured initial interval and doubles per failed attempt, capped at the configured maximum. The implementation does not perform network retries itself; it provides deterministic bounded scheduling input to a future transport layer.

## Latency evidence

The runtime can calculate end-to-end observation latency from timezone-aware send/receive timestamps and stores the most recent measured value. These measurements are evidence when produced by a real transport/runtime environment; the presence of the measurement API is not itself a claim of achieved latency.

## Security / failure boundary

The runtime contains no authentication-token handling, arbitrary payload execution, OS/process manipulation, game-memory access, authorization decision, or action executor. Transport loss degrades Companion health rather than becoming an authorization decision.

## Current limits

This increment does not yet implement network reconnect, watchdog scheduling, persistent telemetry, kill-switch integration, PC launcher transport, WoW addon transport, or real-device/end-to-end latency evidence. Those require the next runtime/integration increment and must remain explicitly unverified until evidence exists.
