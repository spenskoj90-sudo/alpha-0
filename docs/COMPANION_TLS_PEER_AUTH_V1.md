# Companion TLS Peer Authentication Foundation v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

The concrete Companion TCP transport may optionally pin the TLS peer certificate using a SHA-256 fingerprint. This adds a deterministic server-identity check after the TLS handshake and before the transport enters the connected state.

## Contract

- `pinned_peer_sha256` accepts a SHA-256 certificate fingerprint in hexadecimal form, with optional colon separators.
- The configured pin is normalized before comparison.
- The peer certificate is read only in TLS mode and hashed locally with SHA-256.
- A missing/invalid certificate or fingerprint mismatch fails closed.
- A failed pin check closes the underlying socket and leaves the transport disconnected.
- A successful pin check exposes only the normalized fingerprint as local transport metadata.

## Security boundary

Certificate pinning is an additional peer-identity control. It does not replace the existing Companion session authorization boundary and does not grant game-action permission. The session remains responsible for peer authorization before its pre-connection authorization gate, while the TCP transport verifies the TLS server identity after the TLS handshake.

Plaintext loopback/dev mode cannot use certificate pinning and is rejected if both options are requested.

## Evidence boundary

Automated tests prove deterministic fingerprint normalization, hashing, matching, mismatch rejection and connected-state behavior using mocked TLS sockets. This is implementation/security evidence, not production certificate deployment evidence. Production certificate custody and live deployment remain Owner-gated.
