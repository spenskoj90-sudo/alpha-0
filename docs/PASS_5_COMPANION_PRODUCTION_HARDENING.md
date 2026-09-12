# PASS 5 — Companion Production Hardening

**Status:** ACTIVE IMPLEMENTATION / VALIDATION CONTRACT

## Scope

PASS 5 hardens the existing Companion transport boundary without changing the
product authority model. Companion remains a transport and observation channel;
it does not authorize game actions, mutate authoritative UGS state, or execute
commands.

## Security invariants

- Production TCP transport requires an explicit TLS context unless the caller
  explicitly opts into plaintext for local development or tests.
- Real `ssl.SSLContext` instances must enforce TLS 1.2 or newer.
- Real TLS contexts must require certificate verification (`CERT_REQUIRED`) and
  hostname verification.
- Optional SHA-256 certificate pinning remains an additional peer-identity
  control and fails closed on mismatch, empty certificates, or invalid pins.
- A failed TLS pin check never transitions the transport into `connected` state.
- Peer authorization is evaluated by the Companion session before the bound
  transport opens its network connection.
- Frame size is bounded before socket writes.
- Kill-switch state prevents queue admission and reconnect/start operations.

## Reliability boundary

The existing runtime retains bounded heartbeat watchdog state, exponential
reconnect scheduling, bounded FIFO queue/backpressure, explicit transport
failure degradation, and bounded telemetry. This pass adds configuration-level
TLS enforcement and regression coverage around the security boundary rather
than introducing a second transport lifecycle.

## Evidence boundary

Automated tests provide implementation evidence for TLS configuration
requirements, certificate verification, fingerprint pinning, loopback transport,
peer authorization ordering, frame limits, kill-switch behavior, and transport
lifecycle. They do not constitute evidence of production certificate custody,
real-device latency, internet-facing deployment, or live Companion/WoW
operation. Production certificates, credentials, and live deployment remain
Owner-gated.
