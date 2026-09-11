# SENTINEL Companion Runtime Telemetry Factory v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Provide a single transport-neutral constructor for Companion runtime telemetry. The default is a bounded local sink; an optional persistent sink is composed through the existing fanout boundary.

## Safety boundary

- Telemetry remains observational and bounded.
- Persistent storage is optional and injected by the caller.
- No provider, authorization, action execution or network behavior is introduced.
- The factory does not silently swallow sink failures.

## Evidence boundary

This defines deterministic runtime telemetry construction. It does not claim production telemetry deployment or measured production performance.
