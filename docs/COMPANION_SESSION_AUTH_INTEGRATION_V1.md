# Companion Session Peer-Auth Integration v1

## Purpose

This increment binds the existing Companion peer-authentication boundary to the transport session and the loopback WebSocket transport.

The session now accepts optional `PeerAuthEvidence` through `CompanionPeerAuthenticator` before entering the active runtime state. When an authenticator is configured, missing evidence and rejected peers fail closed and the runtime is not activated.

## Transport integration

`CompanionWebSocketTransport.accept()` now:

1. enforces the existing loopback-only network boundary;
2. derives bounded loopback peer evidence;
3. passes that evidence through the peer authenticator;
4. activates the runtime only after authorization succeeds.

The default WebSocket path uses `AllowlistPeerAuthenticator` for the already-enforced loopback peer. This is deterministic local/test scaffolding, not cryptographic remote identity.

Custom authenticators and evidence factories can be supplied by a future production transport/security adapter without changing the session contract.

## Security boundary

- Missing peer evidence is denied when session authentication is configured.
- Unauthenticated evidence is denied.
- Unknown peer identifiers are denied by the allowlist authenticator.
- A failed peer decision never activates the Companion runtime.
- Authorization remains distinct from action execution and policy authorization.
- No credentials, certificates, signing keys, or production identity infrastructure are introduced.

## Evidence boundary

This increment proves the code-level integration seam and loopback socket behavior through automated tests. It does **not** claim production certificate-based peer authentication, remote identity management, or real-device/end-to-end transport latency evidence.
