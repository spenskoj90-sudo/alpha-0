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
- player-visible account, entitlement, Companion connection/degraded state and WoW checkpoint queue/delivery feedback;
- deterministic Node tests executed by the repository `Build & Test` workflow, including static Classic/Retail addon and overlay isolation contract checks.

## Run

```bash
cd launcher
npm install
npm start
```

The main renderer cannot execute arbitrary Node commands and never receives Core access or refresh tokens. It communicates only through the isolated preload bridge. The overlay is more restricted: it has a dedicated preload that exposes only a one-way `overlay:snapshot` subscription, accepts no renderer-originated IPC action, is non-focusable/click-through, and renders presentation text with DOM `textContent` rather than HTML injection.

Game executable paths and the bounded WoW observation queue are stored in the Electron application-data directory with restrictive file permissions where supported; authentication secrets are not written there.

The Companion worker connects only to the Core loopback WebSocket endpoint. Browser-compatible authentication uses an opaque auth-bearing WebSocket subprotocol; the bearer value is not placed in the URL and Core selects only the public `sentinel.v1` subprotocol. Core remains authoritative for session validity and ACTIVE subscription-derived Companion access, including live-session revocation when the entitlement leaves ACTIVE state.

## WoW passive checkpoint ingestion

The Classic and Retail addon variants write a bounded coarse snapshot into their declared `SentinelDB` SavedVariables object. The snapshot contains schema/sequence/time, patch and server profile, realm, bounded latency, addon-loaded state and coarse combat state. It deliberately does not persist the player/character name and it contains no action or automation contract.

The launcher discovers `WTF/Account/*/SavedVariables/Sentinel.lua` beneath the configured World of Warcraft executable directory. A process-level `SENTINEL_WOW_SAVEDVARIABLES_PATH` override may be used for controlled development/test environments; it must be an absolute path whose basename is `Sentinel.lua`. Renderer JavaScript cannot choose an arbitrary read path.

SavedVariables are **checkpoint**, not realtime IPC. WoW writes them to disk on its normal SavedVariables lifecycle (for example logout/ReloadUI); the launcher must not imply live addon streaming. Parsed checkpoints are marked low-quality passive evidence and remain queued until an ACTIVE Companion connection delivers them. Core validates them through `ConservativeWowAdapter`, overrides launcher/account association from server-authoritative state and responds with `WOW_OBSERVATION_ACK`. Accepted checkpoints also produce a bounded server-authored `OVERLAY` status presentation. This path does not grant or require `game:write` and does not persist an action-capable event.

## Overlay authority boundary

Core presentations use the existing `CompanionPresentation` contract and carry only presentation id, channel, kind, bounded text, optional confidence and bounded provenance. The worker normalizes only `HEALTH`/`UGS_UPDATE` presentation envelopes, the parent process sanitizes them again, and the overlay store is bounded and time-limited. Unknown fields such as commands, credentials or arbitrary renderer instructions are dropped rather than forwarded.

This composition does **not** establish a voice provider, microphone capture, speech synthesis, exact WoW/private-server compatibility, signed desktop packaging or production-host acceptance. Exact Retail and WotLK 3.3.5a/private-server runtime evidence remains a separate L3/environment gate.
