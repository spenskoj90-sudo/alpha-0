# SENTINEL Platform RC

**Status: SUPERSEDED** — historical feature-branch report. Use `docs/SENTINEL_CURRENT_STATE.md`, current code/tests and exact-SHA CI evidence.

This document describes the implementation added by `agent/sentinel-complete-platform`.

## Product surfaces

- Android Sentinel client with device identity and Diablo catalog.
- Next.js personal control plane at `/`.
- Next.js administrative control plane at `/admin`.
- FastAPI Sentinel Core.
- Electron desktop launcher.
- PostgreSQL schema/migrations for identity, device binding, RBAC, scope, games, subscriptions, entitlements and audit.

## Authoritative Diablo catalog

- Diablo — Windows
- Diablo II — Windows
- Diablo II: Resurrected — Windows
- Diablo III — Windows
- Diablo IV — Windows
- Diablo Immortal — Android

## Security invariants

The server remains authoritative. Client input does not grant roles, permissions or entitlements. Game access requires a server session, an applicable authorization policy and an active entitlement for the requested game. Administrative operations fail closed unless both `SENTINEL_ADMIN_TOKEN` and the RFC 6238 `SENTINEL_ADMIN_TOTP_SECRET` are configured and the request presents both valid factors.

## Required environment

Server:

```text
SENTINEL_ADMIN_TOKEN=<high-entropy secret>
SENTINEL_ADMIN_TOTP_SECRET=<base32 authenticator seed>
DATABASE_URL=postgresql+psycopg://...
```

Web:

```text
SENTINEL_CORE_URL=https://sentinel-core.example
```

## Evidence status

Source changes are committed on the feature branch and exposed through the draft pull request. This environment does not provide a local Android SDK/emulator, PostgreSQL runtime, Node package installation, or a live GitHub Actions runner for this branch. Therefore build, integration, runtime, security-in-environment and performance results remain UNKNOWN until an actual runner executes them.

No benchmark claim is made by this document.
