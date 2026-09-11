# SENTINEL Companion Runtime Builder v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Provide one construction seam for Companion runtime instances with bounded local telemetry enabled by default.

## Contract

- Explicit telemetry injection is preserved.
- Without an injected sink, the existing bounded telemetry factory supplies local telemetry.
- Runtime lifecycle, kill-switch, reconnect and authorization semantics remain owned by `CompanionRuntime` / `CompanionTransportSession`.
- No network connection or persistent storage is opened by the builder.

## Evidence boundary

This establishes deterministic runtime construction. It does not claim production telemetry deployment or live network acceptance.
