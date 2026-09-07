# SENTINEL — Companion TCP Transport v1

**Status:** ACTIVE FOUNDATION  
**Version:** 1.0

## Purpose

This increment provides the first concrete network transport for Companion: a bounded, length-prefixed TCP byte channel for `CompanionEnvelope` messages.

## Wire contract

Each outbound message is encoded as:

1. four-byte unsigned network-order frame length;
2. UTF-8 JSON body produced from the validated `CompanionEnvelope`;
3. deterministic JSON separators and sorted keys.

The transport rejects frames larger than its configured limit. The configured limit defaults to 64 KiB and cannot exceed 1 MiB.

## Security boundary

TLS is required by default. Plaintext TCP is available only through explicit `allow_insecure=True` opt-in for local development or tests. This module does not authenticate peers, authorize actions, execute commands, or manipulate a game process.

Production deployment must provide a validated TLS context and an external identity/authentication policy before this transport is considered production-ready.

## Failure behavior

Connection establishment is explicit. `send()` fails closed when disconnected and closes the socket after an I/O error. `close()` is idempotent. Reconnect policy remains owned by `CompanionRuntime` / `CompanionTransportSession`; this transport does not silently retry writes.

## Verification boundary

Automated tests exercise real localhost TCP I/O, frame decoding, connection preconditions, bounded frames and idempotent close. This is concrete network-transport evidence, but it is **not** real Android-device, launcher, WoW-addon, Internet-path, TLS interoperability, authentication, or end-to-end latency evidence.
