# Android Shared HTTP Transport Boundary v1

SENTINEL Android API clients use one injectable HTTP transport boundary in `com.alpha0.app.net` instead of opening independent `HttpURLConnection` instances in Auth, Device, Event Sync and Dashboard code.

## Contract

`HttpTransport.execute(HttpRequest)` is the only client-level network execution seam. `UrlConnectionHttpTransport` is the JVM/Android implementation and owns connection creation, connect/read timeouts, request headers/body writing, response reading and connection cleanup.

The API clients still own their application semantics:

- Auth owns credential/refresh JSON and session parsing.
- Device owns bind/challenge/proof payloads, signatures and `game:write` scope validation.
- Event Sync owns batch size, deterministic idempotency keys and per-request `X-Request-ID` generation.
- Dashboard owns caller-scoped read/device-management endpoint parsing.

Transport consolidation does not grant scopes, create authorization decisions, alter device proof, or add retries.

## Security and resource behavior

- HTTPS uses the platform TLS stack and hostname verification; no trust-all TLS or custom permissive verifier is installed.
- Only `http` and `https` schemes are accepted. HTTP remains available for the repository's local loopback development configuration.
- Automatic redirects are disabled so Authorization-bearing requests cannot be silently redirected to another origin.
- Default connect/read timeouts remain 10s/15s.
- Response bodies are bounded to 1 MiB before UTF-8 conversion.
- Header CR/LF injection is rejected.
- The transport performs a single attempt. Retry/idempotency policy remains caller-specific rather than implicit in the HTTP layer.
- Connections are disconnected in `finally`.
- Transport exceptions are mapped by API clients to stable fail-closed error codes; Dashboard no longer exposes exception class/message text to callers.

## Testability

All four API surfaces accept an injected `HttpTransport`, so request method, URL, headers, body and error mapping are unit-testable without opening a real network connection. Transport-level tests exercise timeout policy, disabled redirects, bounded response handling, single connection creation and unsupported-scheme rejection.

## Evidence boundary

Repository tests and GitHub Emulator CI prove the shared boundary and Android regression behavior. They do not by themselves establish production-network performance, physical-device acceptance, certificate/pinning policy beyond platform defaults, or production release readiness.
