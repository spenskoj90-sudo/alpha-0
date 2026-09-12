# SENTINEL Companion Experience Runtime v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Composed path

The Block C runtime composes the existing bounded primitives in one deterministic
pass:

`authenticated Companion UGS_UPDATE → conservative WoW adapter → UGS ingest → projections → provider-neutral recommendation → health/provenance presentation → bounded outbound queue`

`CompanionExperienceRuntime.process_update()` requires an authenticated
transport session, preserves the UGS sequence/replay boundary, and returns a
single `CompanionExperienceSnapshot` containing current state, recommendation,
health, entitlement state, warnings, provenance/confidence presentations, and
explicit capability claims.

## Durability and recovery

Android `OfflineEventQueue` now supports an optional atomic JSON journal with
bounded item and byte capacity. Enqueue and acknowledgement are persisted;
reopening the queue restores pending events, and malformed local state is
isolated by starting an empty queue. `EventSyncCoordinator` retains events on
failed sends for retry.

The server transport queue remains bounded FIFO with drop accounting, stop/reset
semantics, reconnect backoff and watchdog degradation. No queue path executes an
action or silently bypasses authentication.

## Voice and presentation boundary

`VoiceBoundary` provides provider-neutral STT/TTS seams. Consent, audio/text
limits and provider availability are checked before provider I/O. Voice command
classification produces only `OBSERVE`, `ACKNOWLEDGE`, or `DISMISS`
`InteractionIntent` values. Action-like language is rejected with
`ACTION_GATEWAY_REQUIRED`; no voice path can execute a game action.

## WoW evidence scope

The addon and adapter remain passive telemetry only. This increment implements
and tests the local protocol/UGS/recommendation composition and marks the
following claims explicitly:

- `wow-observation`, presentation contract, and queue persistence: implemented;
- provider-specific STT/TTS and production overlay renderer: seam only,
  environment-unverified;
- exact WoW 3.3.5a/private-server L3 capability behavior: external/Owner gate,
  still `UNVERIFIED`.

No document in this repository treats simulation or unit tests as real-device,
real-launcher, or live private-server evidence.

