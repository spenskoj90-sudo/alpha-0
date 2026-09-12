# PASS 4 — Intelligence Completion

## Scope

PASS 4 completes the deterministic intelligence vertical from normalized UGS context through bounded knowledge derivation and provider routing into recommendation evidence:

`UGS -> bounded recommendation context -> Knowledge Engine -> provider routing -> recommendation -> confidence/provenance`

This pass deliberately does **not** introduce external AI network calls, provider credentials, privileged actions, entitlement mutation, billing mutation, or game-command execution.

## Implemented

- `server/app/core/knowledge_engine.py`
  - derives bounded `fact` and `inference` items from normalized recommendation context;
  - preserves explicit confidence and provenance;
  - degrades inference confidence for weak data quality;
  - fails toward an explicit low-evidence state instead of inventing facts.
- `server/app/core/ai_provider.py`
  - baseline provider now consumes Knowledge Engine output rather than ignoring context;
  - provider registry remains explicit and fail-closed;
  - provider metadata exposes only provider/model identity and default state.
- `server/tests/test_knowledge_engine.py`
  - fact/inference derivation;
  - evidence degradation;
  - bounded projection and raw-payload exclusion.
- `server/tests/test_ai_provider.py`
  - deterministic routing;
  - unknown-provider rejection;
  - recommendation confidence/provenance derived from knowledge evidence.

## Security boundary

1. AI output remains observational and advisory.
2. Unknown provider IDs fail closed.
3. No provider credentials are accepted from request context.
4. Raw adapter payloads do not cross into the knowledge/provider projection.
5. Confidence is bounded to `[0,1]` and provenance is mandatory.
6. Low-evidence context cannot produce a high-confidence recommendation.
7. No AI result can authorize entitlement, billing, device, or game actions.

## Evidence boundary

This pass proves the Core-side deterministic intelligence contract and provider-routing seam. It does **not** claim a live external AI provider, production provider credentials, production network connectivity, semantic search/vector infrastructure, or a deployed Command Center integration. Those remain later environment/acceptance work.
