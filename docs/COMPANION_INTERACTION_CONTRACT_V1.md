# Companion Overlay / Voice Interaction Contract v1

## Purpose

This contract defines the bounded presentation boundary for Companion overlay and voice surfaces. It carries status, recommendation and alert text without introducing an action protocol.

## Contract

`CompanionPresentation` contains:

- an explicit `OVERLAY` or `VOICE` presentation channel;
- a bounded `STATUS`, `RECOMMENDATION`, or `ALERT` kind;
- text limited to 2,000 characters;
- a correlation identifier for tracing one presentation across surfaces;
- optional confidence in the inclusive range 0..1;
- bounded provenance metadata;
- a per-instance presentation identifier.

`for_channel()` permits the same presentation to be routed to another explicit presentation surface while preserving presentation and correlation identity.

## Security and authority boundary

Presentation is observational and user-facing only. The contract has no command, execution, authorization, credential or game-manipulation fields. `action_capable` is explicitly false.

The launcher overlay implementation preserves that boundary end-to-end:

- Core emits only bounded presentation payload fields over authenticated loopback Companion transport;
- the Companion worker accepts presentation payloads only from known `HEALTH`/`UGS_UPDATE` envelopes and allowlist-normalizes them;
- Electron main sanitizes the normalized presentation again before storing it;
- the store is bounded and time-limited;
- the overlay runs in a dedicated sandboxed, context-isolated, non-Node, non-focusable, click-through BrowserWindow;
- its preload exposes only a one-way snapshot subscription, with no renderer-originated IPC action;
- renderer text is assigned with DOM `textContent`, not HTML evaluation.

The overlay therefore does not authorize or execute gameplay actions and does not receive Core account credentials.

## Failure and resource discipline

Invalid or unbounded text, confidence, provenance, channel or kind is rejected before rendering. Unknown payload fields are dropped rather than copied through. The launcher retains at most a small bounded set of recent presentations and expires them automatically.

## Runtime status

The read-only launcher overlay runtime is implemented for server-authored `OVERLAY` presentation messages, including the passive WoW checkpoint acceptance status emitted by Core. This establishes an end-to-end Core → Companion worker → Electron parent → isolated overlay presentation path.

## Scope boundary

This does **not** claim a production voice provider, microphone ingestion, speech-to-text, text-to-speech, real-device overlay latency evidence, signed desktop packaging, exact WoW/private-server compatibility or production-host acceptance. The `VOICE` contract and provider-neutral `VoiceBoundary` remain implemented/tested seams until an explicit provider/device integration is selected and validated.
