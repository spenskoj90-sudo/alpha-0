# SENTINEL Companion Voice Runtime v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

This contract defines the first player-facing voice runtime for the Electron Companion surface. It is deliberately presentation-only. Voice may observe current presentation state, acknowledge a presentation, or dismiss a presentation. It cannot authorize or execute gameplay actions.

## Runtime composition

The implemented repository path is:

`explicit launcher consent → trusted main-renderer media permission → bounded push-to-talk WebM/Opus capture → Electron main validation → authenticated Core session → ACTIVE companion feature check → provider-neutral STT → server-authoritative intent classification → bounded presentation-only result → local overlay intent application → optional fixed-text provider-neutral TTS feedback`

The renderer never receives the Core access or refresh token. It also cannot choose the recommendation/presentation identifier used for classification and it cannot submit arbitrary text to TTS. Electron main resolves the current bounded overlay presentation identifier and maps classified results to a fixed feedback phrase allowlist.

## Consent and capture boundary

- Voice consent defaults to disabled and is held only in Electron main-process memory.
- Sign-out and main-window close clear consent.
- Electron permission handlers are default-deny. The `media` permission is granted only to the trusted launcher main `webContents` while consent is active and the request originates from the local `file://` launcher surface.
- Display/screen capture is explicitly denied by the launcher session handler.
- Renderer code requests `audio` only and `video: false`.
- Capture format is fixed to `audio/webm;codecs=opus`.
- Capture duration is capped at six seconds and the byte payload is capped at 512,000 bytes before Core/provider I/O.
- No background-listening loop exists. Capture begins only after the player invokes push-to-talk.

Electron's `media` permission is a Chromium/Electron permission category and is not represented here as a stronger OS guarantee than the API provides. The implementation additionally constrains the trusted renderer capture request to audio-only.

## Core authority and privacy

The Core voice endpoints require:

1. a valid opaque Core session;
2. existing `game:read` authorization;
3. an ACTIVE subscription-derived `companion` feature;
4. explicit `consent_granted=true` for STT/TTS operations;
5. bounded locale, recommendation id, text and audio payloads.

Raw audio and STT transcript are not written to SENTINEL audit records. The transcribe response intentionally omits the transcript. Audit records carry only actor/device identity already owned by Core, action/resource, request/correlation id, decision and a bounded reason code.

Server-side classification permits only:

- `OBSERVE`;
- `ACKNOWLEDGE`;
- `DISMISS`.

Action-like language is rejected as `ACTION_GATEWAY_REQUIRED`. The voice runtime does not acquire `game:write`, does not call the Action Gateway to execute an action, and does not synthesize authority from an entitlement or presentation.

## Provider-neutral STT/TTS adapter

Core exposes a vendor-neutral HTTP adapter when `SENTINEL_VOICE_PROVIDER_URL` is configured:

- `POST <provider>/v1/stt` receives bounded base64 WebM/Opus plus locale and returns `{ "transcript": "..." }`;
- `POST <provider>/v1/tts` receives bounded text plus locale and returns bounded base64 WAV plus `content_type: audio/wav`.

Non-loopback provider URLs must use HTTPS. Optional bearer credentials are injected through `SENTINEL_VOICE_PROVIDER_TOKEN`; they are not embedded in the repository, API response, renderer state or audit metadata. Loopback HTTP is permitted for deterministic/local integration.

If no provider is configured, the runtime reports `VOICE_PROVIDER_UNAVAILABLE` and performs no hidden browser speech-service fallback. Provider exceptions become bounded `VOICE_PROVIDER_FAILED` outcomes.

## Player feedback and TTS

Electron main applies accepted voice intents only to the local overlay presentation store:

- `ACKNOWLEDGE` and `DISMISS` may remove the referenced bounded presentation;
- `OBSERVE` may surface the existing read-only overlay;
- no intent can invoke game input or mutate game state.

Optional TTS feedback text is selected in Electron main from a fixed mapping such as `Acknowledged.` or `Voice cannot execute game actions.`. The renderer has no arbitrary synthesis IPC method. Synthesized audio is validated again in main before the bounded WAV is returned for local playback.

## Failure and resource behavior

The runtime fails closed for missing session, missing entitlement, missing consent, invalid locale/base64, oversized audio/text/output, malformed provider responses, unavailable provider, provider failure and malformed Core responses. A TTS failure degrades feedback without converting an already classified STT intent into a game action or retrying arbitrary text.

Core session calls use the existing one-time refresh rotation path after a single 401. Tokens remain in Electron main-process memory; voice request/status DTOs contain no token fields.

## Evidence classification

Repository and routine CI can establish:

- **IMPLEMENTED / INTEGRATION-TESTED:** consent state machine, permission handlers, bounded capture contract, authenticated voice API, entitlement enforcement, provider adapter, server-authoritative intent classification, local overlay intent application, TTS feedback composition and privacy/failure tests.
- **ENVIRONMENT-UNVERIFIED:** real microphone/driver behavior on the release host, selected production STT/TTS vendor/network behavior, acoustic quality/latency, signed desktop package behavior and exact WoW/private-server environment acceptance.
- **OWNER/EXTERNAL GATE:** production provider credentials, signing material, release publication and live deployment.

Deterministic stub/provider tests must not be reported as production voice-provider or physical microphone acceptance evidence.
