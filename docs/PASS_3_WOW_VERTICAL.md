# PASS 3 — WoW Real Vertical Slice

## Scope

PASS 3 establishes one executable Core-side vertical boundary:

`WoW observation -> conservative adapter -> Companion UGS_UPDATE ingress -> UGS -> deterministic projection -> bounded recommendation context -> recommendation application`

The implementation is intentionally transport-neutral. The existing Companion transport/session remains responsible for connection, peer authentication, queueing, TLS-capable transport composition, reconnect and health. The new vertical slice consumes an already-authenticated Companion envelope and does not open sockets or duplicate TLS/authentication.

## Implemented seam

`server/app/core/wow_vertical_slice.py` provides:

- `ingest_observation()` for a normalized passive WoW observation;
- `ingest_companion_envelope()` for authenticated `UGS_UPDATE` envelopes;
- strict session sequence enforcement through `UGSIngestor`;
- construction of validated `UGSState` using the existing adapter identity/capability contract;
- deterministic `UGSProjectionRegistry` application;
- bounded `recommendation_context()` projection, excluding raw adapter payloads;
- handoff to the existing `RecommendationApplication` seam.

## Security invariants

1. Only `UGS_UPDATE` Companion messages are accepted by the vertical ingress.
2. Companion ingress requires an already-authenticated peer; otherwise it fails closed.
3. Sequence replay is rejected by the UGS ingestion state machine.
4. WoW data remains passive observation data and cannot encode or authorize a game action.
5. Recommendation context is bounded and does not copy raw adapter payloads.
6. No external provider or network operation is introduced by this slice.

## Evidence level

This pass provides executable contract/integration evidence for the Core-side vertical path. It does **not** claim a live World of Warcraft 3.3.5a/private-server L3 environment, real addon socket transport, production TLS deployment, or external AI provider runtime.

Those remain acceptance gates for the later real-environment pass.

## Test coverage

`server/tests/test_wow_vertical_slice.py` covers:

- observation -> UGS -> projection -> recommendation;
- duplicate/sequence replay rejection;
- authenticated Companion `UGS_UPDATE` ingress;
- unauthenticated peer rejection;
- non-UGS Companion message rejection.
