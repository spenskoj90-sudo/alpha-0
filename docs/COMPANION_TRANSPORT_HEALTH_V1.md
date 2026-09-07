# SENTINEL — Companion Transport Health v1

**Status:** ACTIVE FOUNDATION  
**Version:** 1.0

## Purpose

This increment binds the Companion protocol queue to the runtime lifecycle without choosing a concrete network transport. It makes transport health observable through a small, provider-neutral session seam.

## Session boundary

`CompanionTransportSession` owns:

- runtime lifecycle start/stop state;
- bounded protocol queue admission and FIFO consumption;
- explicit transport-failure degradation;
- deterministic reconnect-attempt scheduling delegated to `CompanionRuntime`;
- last successful send timestamp;
- a bounded health snapshot containing mode, heartbeat, latency, reconnect attempts, queue depth and dropped-event count.

A concrete transport is expected to call the seam when its own I/O succeeds or fails. The seam does not open sockets, perform retries, authenticate, authorize, execute actions, or manipulate a game process.

## Failure behavior

Transport failure produces `DEGRADED`, not an authorization decision. An explicitly closed session is `STOPPED` and rejects further enqueue/reconnect operations. Queue overflow remains visible through the existing dropped-event counter.

## Privacy

The health snapshot contains operational state only. It does not include user identifiers, chat, raw game payloads, authentication tokens or session credentials.

## Verification boundary

Automated tests cover session/queue/lifecycle state transitions and health reporting. This does **not** constitute real network, launcher, WoW-addon, real-device or end-to-end latency evidence. Those remain unverified until an actual transport/runtime environment produces exact-SHA evidence.
