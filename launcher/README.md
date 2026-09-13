# SENTINEL Launcher

Electron desktop launcher and local Companion control surface.

The launcher currently provides:

- Windows executable launch entries for World of Warcraft and the existing Diablo catalog;
- Core account sign-in with opaque access/refresh tokens retained only in Electron main-process memory;
- server-derived `companion` feature readback before Companion start;
- a dedicated Companion worker process with protocol handshake, heartbeat, bounded reconnect/backoff, refresh handoff and an explicit stop/kill switch;
- passive WoW addon checkpoint ingestion from the addon's own `SentinelDB` SavedVariables file through a strict non-evaluating Lua-subset parser;
- a bounded disk-backed FIFO for parsed WoW observations, one-at-a-time Companion delivery and explicit Core ACK removal;
- a read-only click-through Companion overlay in its own sandboxed Electron window, fed only by bounded Core `OVERLAY` presentations plus sanitized Companion/checkpoint status;
- explicit-consent push-to-talk capture with sender-bound five-second microphone permission leases, default-deny Electron permission handlers, bounded WebM/Opus capture, authenticated Core STT intent classification and optional bounded WAV TTS feedback;
- player-visible account, entitlement, Companion connection/degraded state, WoW checkpoint queue/delivery state and voice provider/consent/result feedback;
- deterministic Node tests executed by the repository `Build & Test` workflow, including static Classic/Retail addon, overlay isolation and voice permission/capture contract checks.

## Run

```bash
cd launcher
npm install
npm start
```

The main renderer cannot execute arbitrary Node commands and never receives Core access or refresh tokens. It communicates only through the isolated preload bridge. The overlay is more restricted: it has a dedicated preload that exposes only a one-way `overlay:snapshot` subscription, accepts no renderer-originated action IPC, is non-focusable/click-through, and renders presentation text with DOM `textContent` rather than HTML injection.

Game executable paths and the bounded WoW observation queue are stored in the Electron application-data directory with restrictive file permissions where supported; authentication secrets and voice consent are not written there.

The Companion worker connects only to the Core loopback WebSocket endpoint. Browser-compatible authentication uses an opaque auth-bearing WebSocket subprotocol; the bearer value is not placed in the URL and Core selects only the public `sentinel.v1` subprotocol. Core remains authoritative for session validity and ACTIVE subscription-derived Companion access, including live-session revocation when the entitlement leaves ACTIVE state.

## WoW passive checkpoint ingestion

The Classic and Retail addon variants write a bounded coarse snapshot into their declared `SentinelDB` SavedVariables object. The snapshot contains schema/sequence/time, patch and server profile, realm, bounded latency, addon-loaded state and coarse combat state. It deliberately does not persist the player/character name and it contains no action or automation contract.

The launcher discovers `WTF/Account/*/SavedVariables/Sentinel.lua` beneath the configured World of Warcraft executable directory. A process-level `SENTINEL_WOW_SAVEDVARIABLES_PATH` override may be used for controlled development/test environments; it must be an absolute path whose basename is `Sentinel.lua`. Renderer JavaScript cannot choose an arbitrary read path.

SavedVariables are **checkpoint**, not realtime IPC. WoW writes them to disk on its normal SavedVariables lifecycle (for example logout/ReloadUI); the launcher must not imply live addon streaming. Parsed checkpoints are marked low-quality passive evidence and remain queued until an ACTIVE Companion connection delivers them. Core validates them through `ConservativeWowAdapter`, overrides launcher/account association from server-authoritative state and responds with `WOW_OBSERVATION_ACK`. Accepted checkpoints also produce a bounded server-authored `OVERLAY` status presentation. This path does not grant or require `game:write` and does not persist an action-capable event.

## Overlay authority boundary

Core presentations use the existing `CompanionPresentation` contract and carry only presentation id, channel, kind, bounded text, optional confidence and bounded provenance. Presentation traffic uses the dedicated `PRESENTATION` Companion envelope type; `HEALTH` is reserved for correlated runtime-health telemetry and `UGS_UPDATE` retains game-state/update semantics. The worker accepts only `PRESENTATION` envelopes for overlay content, the parent process sanitizes the presentation again, and the overlay store is bounded and time-limited. Presentation-shaped `HEALTH` or `UGS_UPDATE` payloads are not inferred as overlay content. Unknown fields such as commands, credentials or arbitrary renderer instructions are dropped rather than forwarded.

## Voice authority and privacy boundary

Voice is opt-in push-to-talk only. Consent starts disabled, lives only in Electron main-process memory and is cleared on sign-out or main-window close. Consent alone does not keep microphone permission enabled: the trusted main renderer must arm a five-second permission lease immediately before its explicit `getUserMedia` request, and the lease is disarmed immediately after the request resolves or rejects. Voice IPC verifies that the sender is the current main launcher `webContents`; overlay/other renderers cannot arm or submit capture through those channels.

Electron session permission handlers deny permissions by default; `media` is granted only to the trusted launcher main `webContents` while both consent and the short-lived capture lease are active, and display capture is explicitly denied. The renderer itself requests audio-only capture with `video: false`.

Capture uses `audio/webm;codecs=opus`, a six-second maximum and the Core-advertised byte limit capped locally at 512,000 bytes. Renderer audio is validated again in Electron main before it is sent through the authenticated Core session. Capture errors, sign-out and the Companion kill switch discard partial audio rather than submitting it. Core repeats authorization, ACTIVE `companion` entitlement and consent checks before provider I/O.

The renderer does not receive the STT transcript. Core returns only a bounded presentation intent (`OBSERVE`, `ACKNOWLEDGE`, `DISMISS`) or a reason code. Electron main chooses the current bounded presentation identifier; the renderer cannot target an arbitrary recommendation. `ACKNOWLEDGE`/`DISMISS` can only remove local overlay presentation state and `OBSERVE` can only surface the read-only overlay.

Optional TTS is similarly narrow: the renderer has no arbitrary synthesis IPC. Electron main maps the sanitized intent/result to fixed feedback phrases and validates bounded WAV output before passing it to the renderer for local playback. If STT/TTS is not configured, the launcher exposes a provider-unavailable/degraded state rather than invoking a hidden browser speech service.

See `docs/COMPANION_VOICE_RUNTIME_V1.md` for the normative runtime contract.

This composition does **not** establish a selected production voice vendor, production provider credentials, physical microphone/driver acceptance, acoustic quality or latency evidence, exact WoW/private-server compatibility, signed desktop packaging or production-host acceptance. Exact Retail and WotLK 3.3.5a/private-server runtime evidence remains a separate L3/environment gate.
