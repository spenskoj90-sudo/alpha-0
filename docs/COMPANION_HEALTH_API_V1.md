# SENTINEL Companion Health API v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Serialize the existing bounded `CompanionRuntimeHealth` snapshot into a transport-neutral JSON-ready structure.

## Contract

- Health is observational and bounded.
- Queue depth, dropped events, reconnect attempts, latency and lifecycle mode remain explicit.
- Peer authentication state is exposed as state, not authorization.
- The serializer performs no network I/O, authorization or action execution.

## Evidence boundary

This is a serialization seam for the existing health snapshot. It does not claim a public HTTP endpoint or production monitoring integration.
