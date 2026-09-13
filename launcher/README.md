# SENTINEL Launcher

Electron desktop launcher and local Companion control surface.

The launcher currently provides:

- Windows executable launch entries for World of Warcraft and the existing Diablo catalog;
- Core account sign-in with opaque access/refresh tokens retained only in Electron main-process memory;
- server-derived `companion` feature readback before Companion start;
- a dedicated Companion worker process with protocol handshake, heartbeat, bounded reconnect/backoff, refresh handoff and an explicit stop/kill switch;
- player-visible account, entitlement, connection and degraded-state feedback;
- deterministic Node tests executed by the repository `Build & Test` workflow.

## Run

```bash
cd launcher
npm install
npm start
```

The renderer cannot execute arbitrary Node commands and never receives Core access or refresh tokens. It communicates only through the isolated preload bridge. Game executable paths are stored in the Electron application-data directory with restrictive file permissions where supported; authentication secrets are not written there.

The Companion worker connects only to the Core loopback WebSocket endpoint. Browser-compatible authentication uses an opaque auth-bearing WebSocket subprotocol; the bearer value is not placed in the URL and Core selects only the public `sentinel.v1` subprotocol. Core remains authoritative for session validity and ACTIVE subscription-derived Companion access, including live-session revocation when the entitlement leaves ACTIVE state.

This composition does **not** establish real WoW/private-server compatibility, signed desktop packaging, addon SavedVariables ingestion, or production-host acceptance. Those require their own implementation/evidence gates.
