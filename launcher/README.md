# SENTINEL Launcher

Electron desktop control shell for the Windows Diablo catalog.

Supported entries:

- Diablo
- Diablo II
- Diablo II: Resurrected
- Diablo III
- Diablo IV
- Diablo Immortal (Android handoff; Windows launch is intentionally disabled)

## Run

```bash
cd launcher
npm install
npm start
```

The renderer cannot execute arbitrary Node commands. It communicates only through the isolated preload bridge. Windows executable paths are stored in the Electron application data directory with restrictive file permissions where supported.

The launcher is intentionally an integration shell: the authoritative Sentinel server remains responsible for identity, authorization, scope and entitlement decisions before a production launcher should enable a game session.
