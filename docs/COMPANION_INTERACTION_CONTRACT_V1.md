# Companion Overlay / Voice Interaction Contract v1

## Purpose

This contract defines the bounded presentation boundary for Companion overlay and voice surfaces. It carries status, recommendation and alert text and presentation-only interaction intents without introducing a gameplay action protocol.

## Presentation contract

`CompanionPresentation` contains:

- an explicit `OVERLAY` or `VOICE` presentation channel;
- a bounded `STATUS`, `RECOMMENDATION`, or `ALERT` kind;
- text limited to 2,000 characters;
- a correlation identifier for tracing one presentation across surfaces;
- optional confidence in the inclusive range 0..1;
- bounded provenance metadata;
- a per-instance presentation identifier.

`for_channel()` permits the same presentation to be routed to another explicit presentation surface while preserving presentation and correlation identity.

## Interaction authority

`InteractionIntent` is deliberately smaller than a command/action contract. It permits only:

- `OBSERVE` — surface existing read-only presentation state;
- `ACKNOWLEDGE` — acknowledge/remove bounded presentation state;
- `DISMISS` — dismiss bounded presentation state.

`is_action_capable()` remains false. Entitlement, recommendation, overlay presence, voice classification or TTS feedback cannot grant gameplay authority.

Action-like voice language is rejected by Core as `ACTION_GATEWAY_REQUIRED`; the voice runtime does not forward that language into an Action Gateway execution request.

## Overlay security boundary

The launcher overlay implementation preserves the presentation boundary end-to-end:

- Core emits bounded presentation payload fields only on the dedicated `PRESENTATION` Companion envelope type over authenticated loopback transport;
- `HEALTH` remains reserved for correlated runtime-health telemetry and `UGS_UPDATE` retains game-state/update semantics;
- the Companion worker accepts overlay content only from `PRESENTATION` envelopes and allowlist-normalizes it; presentation-shaped `HEALTH` or `UGS_UPDATE` payloads are not inferred as overlay content;
- Electron main sanitizes the normalized presentation again before storing it;
- worker IPC and exit handling are bound to the currently active child process, so a stopped/replaced worker cannot publish stale presentation/status data or apply a delayed refresh result to a new worker;
- the store is bounded and time-limited;
- the overlay runs in a dedicated sandboxed, context-isolated, non-Node, non-focusable, click-through BrowserWindow;
- its preload exposes only a one-way snapshot subscription, with no renderer-originated action IPC;
- renderer text is assigned with DOM `textContent`, not HTML evaluation.

Invalid or unbounded text, confidence, provenance, channel or kind is rejected before rendering. Unknown payload fields are dropped rather than copied through.

## Voice security and privacy boundary

Voice is explicit push-to-talk, not background listening.

- Consent defaults disabled and exists only in Electron main-process memory.
- Sign-out and main-window close clear consent.
- Electron permission handlers deny by default and grant `media` only to the trusted launcher main webContents while consent is active and the page is local `file://` content.
- Display/screen capture is explicitly denied.
- Renderer capture requests audio only (`video: false`), fixed WebM/Opus, maximum six seconds and a bounded byte payload.
- Electron main validates audio/base64/locale again before Core transport.
- Core repeats session, `game:read`, ACTIVE `companion` feature and explicit consent checks before provider I/O.
- Raw audio and transcript are omitted from SENTINEL audit metadata; transcript is also omitted from the Core transcribe response.
- Electron main, not renderer JavaScript, chooses the bounded current presentation identifier used for the interaction intent.
- Accepted `ACKNOWLEDGE` or `DISMISS` can affect only local bounded overlay presentation state. `OBSERVE` can surface the existing read-only overlay.
- Renderer JavaScript has no arbitrary synthesis-text IPC. Main selects feedback text from a fixed mapping and validates bounded WAV before playback.

## Provider boundary

The Core provider-neutral `VoiceBoundary` is composed with an optional JSON-over-HTTP adapter. Non-loopback endpoints require HTTPS; optional credentials are process-environment inputs and are not exposed through voice status/results or audit metadata.

No provider configured means `VOICE_PROVIDER_UNAVAILABLE`. Provider exceptions become bounded failure codes. There is no implicit browser/cloud speech fallback.

## Runtime status and evidence

The read-only overlay and explicit-consent voice runtime are implemented as repository/runtime compositions. Automated tests cover protocol/type separation, bounded stores, stale-worker isolation, voice DTO sanitization, default-deny permission logic, capture bounds, session refresh, entitlement/consent enforcement, provider failures and transcript non-disclosure.

This establishes **IMPLEMENTED / INTEGRATION-TESTED** repository evidence for the player interaction boundary. It does **not** establish a selected production STT/TTS vendor, production credentials, physical microphone/driver acceptance, acoustic/latency targets, signed desktop packaging, exact WoW/private-server compatibility or production-host acceptance. Those remain environment/external evidence gates.
