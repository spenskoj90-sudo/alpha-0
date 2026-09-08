# SENTINEL — Companion Network Transport v1

**Status:** PROPOSED IMPLEMENTATION CONTRACT
**Version:** 1.0

## Purpose

Define the first concrete network transport for the local Companion ↔ Core path without weakening the existing authorization boundary or pretending that a transport is already device-validated.

## Scope

The first transport is a **loopback WebSocket transport** between a local Companion process and SENTINEL Core.

It is intentionally limited to localhost traffic. Internet-facing Companion transport, reverse proxies, TLS termination, and production deployment are outside this increment.

## Security boundary

The transport is a delivery mechanism, not an authorization source.

- Bind only to loopback by default.
- Reject non-loopback peer addresses.
- Require the existing Companion handshake before accepting application envelopes.
- Fail closed on protocol, UGS schema, adapter contract, Core protocol, or capability-profile mismatch.
- Do not accept arbitrary executable payloads.
- Do not authorize privileged game actions.
- Do not expose authentication tokens or credentials through health snapshots or logs.
- Transport shutdown must stop further queue admission and delivery.

A future authenticated deployment transport may add TLS or another authenticated channel without changing the Companion protocol envelope.

## Framing

Each WebSocket message carries one bounded `CompanionEnvelope` serialized as JSON.

The receiver must validate the complete envelope before queue admission. Invalid, oversized, unknown-field or unsupported-message payloads are rejected without execution.

## Lifecycle

```text
CONNECT
  ↓
HANDSHAKE
  ↓
HANDSHAKE_ACK
  ↓
ACTIVE
  ↓
HEARTBEAT / ENVELOPE FLOW
  ↓
DEGRADED on transport failure
  ↓
RECONNECT with bounded backoff
  ↓
ACTIVE after successful handshake
```

An explicit shutdown is terminal for the session and produces `STOPPED`. A stopped session cannot be revived by a reconnect callback.

## Backpressure

The existing bounded `CompanionQueue` remains authoritative for buffering.

- Producers enqueue through `CompanionTransportSession`.
- The transport drains FIFO entries.
- Queue overflow follows existing drop-oldest accounting.
- Transport code must never allocate an unbounded pending-message buffer.
- Queue depth and dropped-event counts remain visible through the privacy-safe health snapshot.

## Failure semantics

- Connection failure → `DEGRADED` and schedule bounded reconnect.
- Send failure → do not report success; preserve the session's failure state.
- Receive validation failure → reject the message and keep the connection alive only when the protocol permits safe continuation.
- Handshake mismatch → reject and stop the session.
- Explicit close/kill-switch integration → `STOPPED`; no reconnect.

## Latency instrumentation

The transport records timestamps around actual send/receive operations. These timestamps are transport measurements only.

They must not be represented as real device end-to-end latency until a real Companion/device path has produced evidence containing:

- exact source SHA;
- Core/Companion build identifiers;
- device and OS;
- transport mode;
- measurement method;
- sample count and distribution;
- failure/drop counts.

## Privacy

Transport logs and health snapshots must contain operational metadata only. Raw game payloads, chat, authentication credentials and user identifiers are not logged by the transport implementation.

## Testing contract

Automated tests must cover at least:

1. loopback binding policy;
2. handshake success and each compatibility rejection;
3. bounded envelope serialization/deserialization;
4. malformed/oversized payload rejection;
5. FIFO queue/backpressure behavior;
6. transport failure → `DEGRADED`;
7. reconnect scheduling and successful recovery;
8. explicit close → terminal `STOPPED`;
9. no delivery after stop;
10. transport latency timestamp ordering.

A socket-level integration test may prove the transport implementation. It is not a substitute for real-device E2E evidence.

## Non-goals

- Internet-facing transport;
- production deployment;
- production credential management;
- privileged action execution;
- game-process manipulation;
- kill-switch product UX itself;
- claiming real-device latency before device evidence exists.
