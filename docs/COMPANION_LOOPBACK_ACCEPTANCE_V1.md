# Companion Loopback Acceptance v1

This acceptance increment validates the composed Companion session/transport path against a real local TCP socket in automated tests.

## Covered boundaries

1. A bounded `CompanionTransportSession` is composed with the concrete TCP transport.
2. An authorized session opens the TCP transport and delivers a real length-prefixed JSON envelope over loopback.
3. Successful delivery consumes exactly one queued envelope and records local transport elapsed-time evidence.
4. An unauthorized peer is rejected before the concrete TCP connection is attempted.
5. The test uses explicit insecure loopback mode only; production TCP remains TLS-by-default.

## Evidence limitation

This is deterministic local loopback acceptance evidence. It does **not** claim production network latency, WAN behavior, TLS certificate validation against production infrastructure, or exact WoW/private-server validation.
