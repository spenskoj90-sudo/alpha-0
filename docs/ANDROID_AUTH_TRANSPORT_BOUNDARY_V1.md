# Android Auth Transport Boundary v1

Extracts HTTP transport from `AuthApi` behind an injectable interface while preserving the existing `HttpURLConnection` implementation, timeouts, JSON contract and fail-closed error mapping.

The boundary makes authentication API behavior independently testable without opening real network connections. No credentials are logged or persisted by the transport seam.
