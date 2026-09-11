# Companion TCP Session Composition v1

Provides a deterministic construction seam joining `CompanionRuntime`, `CompanionTransportSession` and the existing bounded TLS-by-default TCP transport.

Construction does not open a socket. Peer authentication remains an explicit session dependency and is evaluated before runtime activation. Plaintext requires an explicit local/test opt-in.
