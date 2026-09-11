# Companion Transport Binding v1

This increment closes the transport/session composition seam without changing the underlying protocol or authorization contracts.

## Boundaries

1. `CompanionTransportBinding` delegates peer authentication and authorization to `CompanionTransportSession`.
2. The concrete network transport is connected only after the session accepts supplied authentication evidence.
3. Denied peers therefore do not open the network transport.
4. Queue delivery remains FIFO and bounded; successful delivery consumes exactly one queued envelope.
5. Transport-call elapsed time is local evidence only. It is not production or remote end-to-end latency evidence.
6. Closing the binding closes both the concrete transport and Companion session.
7. No credentials, certificates, signing keys, external AI calls, action execution, deployment, or release operations are introduced.
