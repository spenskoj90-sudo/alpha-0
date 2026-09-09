# Companion Peer Authentication Boundary v1

## Purpose

This increment defines the security boundary between transport-provided peer authentication evidence and Companion peer authorization. It is intentionally provider-neutral and does not introduce production credentials, certificates, secret material, or external identity infrastructure.

## Boundary

`PeerAuthEvidence` contains only bounded evidence metadata: authentication mechanism, peer identifier, and whether the transport/security layer established authentication.

`CompanionPeerAuthenticator` converts that evidence into a fail-closed `PeerAuthDecision`. Authorization is denied when evidence is unauthenticated or the peer is not explicitly allowed.

`AllowlistPeerAuthenticator` is deterministic local/test scaffolding. It does **not** cryptographically authenticate a peer and must not be treated as a production credential verifier.

## Security properties

- Missing or false authentication evidence is denied.
- Unknown peers are denied.
- Successful authorization returns the bounded peer identifier only.
- No action execution, game manipulation, or policy bypass is introduced.
- No production secrets, certificates, signing keys, or permission changes are required.

## Integration boundary

The existing TLS-by-default TCP transport remains responsible only for byte transport. A future production integration may derive `PeerAuthEvidence` from an authenticated TLS or equivalent identity mechanism, then pass the evidence through the authorization boundary before accepting a Companion session.

This PR does not claim production peer authentication, certificate provisioning, remote identity management, or end-to-end transport/session integration.
