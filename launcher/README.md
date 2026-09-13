# SENTINEL Launcher

Electron desktop launcher, local Companion host and player presentation surface.

The launcher currently provides:

- Windows executable launch entries for World of Warcraft and the existing Diablo catalog;
- Core account sign-in with opaque access/refresh tokens retained only in Electron main-process memory;
- server-derived `companion` feature readback before Companion start;
- a dedicated Companion worker process with protocol handshake, heartbeat, bounded reconnect/backoff, refresh handoff and an explicit stop/kill switch;
- passive WoW addon checkpoint ingestion from the addon's own `SentinelDB` SavedVariables file through a strict non-evaluating Lua-subset parser;
- a bounded disk-backed FIFO for parsed WoW observations, one-at-a-time Companion delivery and explicit Core ACK removal;
- a dedicated transparent always-on-top player overlay for bounded Core `PRESENTATION` messages;
- player-visible account, entitlement, Companion connection/degraded state, WoW checkpoint feedback and aggregate overlay activity;
- deterministic Node tests executed by the repository `Build & Test` workflow, including presentation sanitization/resource bounds and static Classic/Retail addon contract checks.

## Run

```bash
cd launcher
npm install
npm start
```

The launcher renderer and overlay renderer cannot execute arbitrary Node commands and never receive Core access or refresh tokens. They communicate only through isolated preload bridges. Game executable paths and the bounded WoW observation queue are stored in the Electron application-data directory with restrictive file permissions where supported; authentication secrets are not written there.

The Companion worker connects only to the Core loopback WebSocket endpoint. Browser-compatible authentication uses an opaque auth-bearing WebSocket subprotocol; the bearer value is not placed in the URL and Core selects only the public `sentinel.v1` subprotocol. Core remains authoritative for session validity and ACTIVE subscription-derived Companion access, including live-session revocation when the entitlement leaves ACTIVE state.

## Player overlay runtime

A server-validated passive WoW checkpoint may feed the existing deterministic UGS/recommendation path. Core returns the checkpoint ACK independently, then emits bounded `PRESENTATION` envelopes for the player surface. Each presentation carries only an explicit channel/kind, bounded text, identities, confidence/provenance and `action_capable=false`.

The worker and main process both validate this contract before content can reach the overlay. The main process holds a bounded in-memory presentation store with per-kind TTLs and deduplication. The overlay is a separate sandboxed, transparent, frameless, non-focusable, mouse-ignoring Electron window. Its renderer writes content with `textContent`; it exposes no game-action, keyboard-hook, screen-capture or arbitrary IPC surface. Stopping Companion, signing out or exiting clears current presentations.

This is a desktop presentation overlay, not an injected DirectX/game-process overlay. It does not establish signed desktop packaging, exact game-host behavior or production-host acceptance.

## WoW passive checkpoint ingestion

The Classic and Retail addon variants write a bounded coarse snapshot into their declared `SentinelDB` SavedVariables object. The snapshot contains schema/sequence/time, patch and server profile, realm, bounded latency, addon-loaded state and coarse combat state. It deliberately does not persist the player/character name and it contains no action or automation contract.

The launcher discovers `WTF/Account/*/SavedVariables/Sentinel.lua` beneath the configured World of Warcraft executable directory. A process-level `SENTINEL_WOW_SAVEDVARIABLES_PATH` override may be used for controlled development/test environments; it must be an absolute path whose basename is `Sentinel.lua`. Renderer JavaScript cannot choose an arbitrary read path.

SavedVariables are **checkpoint**, not realtime IPC. WoW writes them to disk on its normal SavedVariables lifecycle (for example logout/ReloadUI); the launcher must not imply live addon streaming. Parsed checkpoints are marked low-quality passive evidence and remain queued until an ACTIVE Companion connection delivers them. Core validates them through `ConservativeWowAdapter`, overrides launcher/account association from server-authoritative state and responds with `WOW_OBSERVATION_ACK`. This path does not grant or require `game:write` and does not persist an action-capable event.

This composition does **not** establish exact WoW/private-server compatibility, signed desktop packaging or production-host acceptance. Exact Retail and WotLK 3.3.5a/private-server runtime evidence remains a separate L3/environment gate. Voice remains provider-neutral contract code only until microphone/consent/provider runtime and exact-host evidence exist.
