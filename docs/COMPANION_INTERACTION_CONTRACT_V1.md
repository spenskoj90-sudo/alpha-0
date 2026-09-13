# Companion Overlay / Voice Interaction Contract v1

## Purpose

This contract defines the bounded presentation boundary used by Companion player surfaces. It carries status, recommendation and alert text without introducing an action protocol.

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

Core serializes player-facing output into an explicit Companion `PRESENTATION` envelope. The wire payload includes the presentation and correlation identifiers, channel, kind, bounded text, confidence/provenance and `action_capable=false`.

## Security and authority boundary

Presentation is observational and user-facing only. The contract has no command, execution, authorization, credential or game-manipulation authority. `action_capable` is explicitly false.

The Electron Companion worker and main process independently validate the presentation payload before it reaches a renderer. Unsupported channels/kinds, malformed identifiers, unbounded text/provenance/confidence or any action-capable payload fail closed. Renderer code receives only the allowlisted presentation DTO; it does not receive Core tokens.

The player overlay is a separate sandboxed Electron window with context isolation, Node integration disabled, no focus, ignored mouse input and no game-action/control bridge. Presentation text is written with DOM `textContent` rather than interpreted markup.

Authentication, entitlement and transport authority remain owned by the existing Companion session boundary. Presentation cannot bypass those controls and does not grant `game:write`.

## Failure and resource discipline

Invalid or unbounded presentation fields are rejected before rendering. The launcher store is in-memory, deduplicated by presentation identifier, bounded by item count and uses bounded per-kind TTL expiry. Companion stop, account sign-out and application exit clear current presentations.

A valid passive checkpoint ACK is independent from player-presentation generation: presentation failure must not rewrite a successfully validated observation into a false checkpoint rejection. Server presentation failures are fail-closed and auditable.

## Implemented runtime surface

The repository now wires the passive Companion path end-to-end for the desktop overlay:

`server-validated WoW observation → UGS/recommendation composition → bounded PRESENTATION envelope → Companion worker validation → main-process bounded TTL store → isolated overlay renderer`.

The implementation is a desktop always-on-top presentation surface, not an injected DirectX/game-process overlay.

## Scope boundary

This contract and runtime do **not** claim signed/packaged desktop-host acceptance, exact WoW target compatibility, real-device latency evidence, microphone ingestion, a concrete voice provider, speech-to-text, text-to-speech or a production voice experience. Voice remains a provider-neutral bounded seam until those runtime pieces and their evidence exist.
