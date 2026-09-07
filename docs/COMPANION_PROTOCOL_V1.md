# SENTINEL — Companion Protocol v1

**Status:** ACTIVE FOUNDATION  
**Version:** 1.0

## Purpose

The Companion protocol is the bounded transport contract between a local companion/integration process and SENTINEL Core. It carries observations and lifecycle/health messages. It does not itself grant authorization or provide a game-action execution API.

## Compatibility handshake

The handshake identifies and negotiates five independent compatibility dimensions:

- Companion protocol version;
- UGS schema version;
- Game Adapter Contract version;
- Core protocol version;
- capability profile.

The first implementation accepts only protocol `1.0` and exact expected values for the other dimensions. A mismatch fails closed into `STOPPED` rather than silently degrading into an incompatible interpretation.

## Message classes

`HANDSHAKE`, `HANDSHAKE_ACK`, `UGS_UPDATE`, `HEARTBEAT`, `HEALTH`, and `SHUTDOWN` are the initial transport-neutral message types.

Every envelope has a bounded sequence number, UUID message ID, explicit latency class, and a bounded payload dictionary of at most 64 entries. Unknown envelope fields are rejected.

## Backpressure

The reference queue is bounded (default 128, maximum 4096). When full, the oldest buffered observation is dropped and the drop count is observable. Once stopped, the queue is cleared and rejects new messages.

This is deliberately conservative: overload must not become unbounded memory growth.

## Latency classes

- **INTERACTIVE:** <=250 ms budget
- **RESPONSIVE:** 251–1000 ms budget
- **BACKGROUND:** >1000 ms budget

These are protocol classes, not measured achievement claims. Runtime end-to-end measurements remain a later evidence requirement.

## Lifecycle / degraded behavior

Handshake incompatibility enters `STOPPED`. The protocol has explicit `ACTIVE`, `DEGRADED`, and `STOPPED` states so later runtime code can expose loss of health without pretending stale observations are current.

A later runtime layer must add reconnect/backoff, watchdog timing, freshness expiry and kill-switch integration around this contract. Those mechanisms are intentionally not hidden inside the transport model.

## Security boundaries

- The companion is not an authorization authority.
- Capability profiles describe integration evidence; they do not grant permissions.
- No authentication-token, process-memory, anti-cheat, DRM, launcher-bypass or remote-execution payload is defined here.
- Action requests must pass the server-side Policy Engine / Action Gateway.
- Exact-environment capability claims remain subject to adapter evidence and L3 requirements.
