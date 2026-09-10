# Android Auth Transport v1

## Purpose

`AuthApi` uses Kotlin coroutines to move all authentication and refresh network I/O onto `Dispatchers.IO`. UI callers no longer create ad-hoc threads or invoke a blocking HTTP operation directly.

## Contract

- `register`, `login` and `refresh` are `suspend` operations.
- Endpoint paths, JSON request fields and session response fields are unchanged.
- Existing diagnostic operation names and bounded error codes remain unchanged.
- `SessionManager` uses a coroutine `Mutex` so refresh rotation remains serialized. The mutex is held across the suspended network request, therefore concurrent refresh attempts observe the latest persisted refresh token rather than racing on a stale token.
- Compose authentication uses a screen-scoped coroutine. Cancelling the screen coroutine cancels the caller's coroutine work; no token or password is placed in diagnostic fields.

## Failure behavior

Transport failures remain `NETWORK_ERROR`; unexpected failures remain `UNEXPECTED_ERROR`; malformed successful responses remain `AUTH_RESPONSE_INVALID`; server error codes continue to be propagated as before.

Authentication responses contain only bounded session metadata in the application model. Diagnostics record operation/status/error metadata and scope count, never credentials or token values.

## Scope

This increment changes only Android client transport/concurrency architecture. It does not change backend authentication, authorization semantics, session token format, production credentials, signing material, or deployment behavior.

Real-device latency and production endpoint acceptance remain separate evidence gates.
