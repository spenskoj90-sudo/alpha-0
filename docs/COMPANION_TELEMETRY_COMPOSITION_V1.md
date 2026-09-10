# SENTINEL Companion Telemetry Composition v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Provide a small composition seam that lets the Companion runtime use its existing local telemetry sink alone or fan out the same privacy-safe event to a persistent sink.

## Safety boundary

- No event transformation or raw game/chat/user payloads are introduced.
- Persistence remains optional.
- The composition layer performs no authorization, action execution or provider calls.
- Sink failure policy remains owned by the caller; the composition does not silently swallow failures.

## Evidence boundary

This is a transport/storage composition seam. It does not claim production persistence deployment or external telemetry ingestion.
