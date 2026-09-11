# SENTINEL Companion Runtime Integration v2

This increment closes five concrete runtime seams on top of the existing Companion foundation:

1. **Compatibility negotiation integration** — the concrete WebSocket transport now uses the provider-neutral multi-dimension compatibility negotiator instead of the older exact-match helper.
2. **Transport lifecycle telemetry** — connect denial/success, queue backpressure, send success, failure, reconnect scheduling and kill-switch transitions emit bounded `companion.transport.*` telemetry.
3. **Concrete runtime telemetry composition** — the WebSocket transport constructs its default runtime through `build_companion_runtime()`, so bounded local telemetry is active without persistence or vendor coupling.
4. **Concrete send-latency measurement** — the WebSocket send seam measures the elapsed local transport call and feeds the existing latency statistics. This is transport-call evidence, not a claim of remote end-to-end latency.
5. **Regression coverage** — integration tests cover fail-closed peer authorization, compatibility selection, telemetry emission and deterministic latency measurement.

## Security boundary

No credential, signing key, production secret, game-memory access, action execution or authorization policy is introduced. Peer authorization remains fail-closed. Telemetry contains operational metadata only and remains bounded.

## Evidence boundary

The increment does not claim production peer identity, remote end-to-end latency, production SLO attainment or external telemetry-provider delivery. Those require separate exact-environment evidence.
