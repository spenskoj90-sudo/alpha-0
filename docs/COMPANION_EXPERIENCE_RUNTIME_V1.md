# SENTINEL Companion Experience Runtime v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Composed paths

The Block C runtime composes bounded player-experience primitives through two read-only/presentation paths:

`authenticated Companion UGS_UPDATE → conservative WoW adapter → UGS ingest → projections → provider-neutral recommendation → health/provenance presentation → bounded outbound queue → isolated overlay`

`explicit launcher voice consent → bounded push-to-talk capture → authenticated Core voice API → ACTIVE companion entitlement → provider-neutral STT → server-authoritative presentation intent → bounded local overlay intent → optional fixed-text provider-neutral TTS feedback`

`CompanionExperienceRuntime.process_update()` requires an authenticated transport session, preserves the UGS sequence/replay boundary, and returns a single `CompanionExperienceSnapshot` containing current state, recommendation, health, entitlement state, warnings, provenance/confidence presentations, and explicit capability claims.

## Durability and recovery

Android `OfflineEventQueue` supports an optional atomic JSON journal with bounded item and byte capacity. Enqueue and acknowledgement are persisted; reopening the queue restores pending events, and malformed local state is isolated by starting an empty queue. `EventSyncCoordinator` retains events on failed sends for retry.

The server transport queue remains bounded FIFO with drop accounting, stop/reset semantics, reconnect backoff and watchdog degradation. No queue path executes an action or silently bypasses authentication.

The launcher SavedVariables observation queue is separately bounded and durable. Voice capture is intentionally **not** durably queued: audio remains an explicit, short-lived push-to-talk payload and is not persisted by SENTINEL.

## Voice and presentation boundary

`VoiceBoundary` remains the provider-neutral Core STT/TTS seam, but the repository now composes it into the player runtime rather than leaving it as an isolated unit-test contract.

Core voice routes require the existing least-privilege user session, `game:read`, ACTIVE subscription-derived `companion` feature and explicit consent. Audio/text/output limits are checked before/after provider I/O. Raw audio and transcript are not written into audit metadata, and the transcribe API intentionally does not return transcript text to the launcher renderer.

Voice command classification produces only `OBSERVE`, `ACKNOWLEDGE`, or `DISMISS` `InteractionIntent` values. Action-like language is rejected with `ACTION_GATEWAY_REQUIRED`; no voice path can execute a game action or grant `game:write`.

Electron main owns voice consent, Core session credentials, provider calls and the current bounded overlay presentation identifier. The renderer owns only explicit push-to-talk capture and playback of already-sanitized bounded feedback audio. The renderer has no arbitrary TTS-text IPC.

A vendor-neutral HTTP provider adapter can be configured by process environment. Non-loopback endpoints require HTTPS. When no provider is configured, Core reports provider unavailability and performs no hidden browser/cloud fallback.

See `docs/COMPANION_VOICE_RUNTIME_V1.md` for the detailed security, consent and evidence contract.

## WoW and environment evidence scope

The addon and adapter remain passive telemetry only. Repository/runtime composition and CI can establish:

- `wow-observation`, presentation contract, queue persistence and read-only overlay path: implemented/integration-tested;
- launcher consent/permission/capture contract, Core voice API, provider-neutral STT/TTS integration boundary and presentation-only intent application: implemented/integration-tested at repository level;
- selected production STT/TTS vendor/network, physical microphone/driver behavior, acoustic quality/latency and signed desktop-host acceptance: environment-unverified;
- exact WoW 3.3.5a/private-server L3 capability behavior: external/Owner gate, still `UNVERIFIED`.

No document in this repository treats simulation or CI tests as physical microphone, production voice-provider, signed-package, real-device or live private-server evidence.
