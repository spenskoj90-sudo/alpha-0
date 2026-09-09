# AI Provider Abstraction v1

## Scope

This increment introduces a provider-neutral seam for AI inference and recommendation output. It does not add external provider credentials, network calls, autonomous execution, or authorization authority.

## Contract

`server/app/core/ai_provider.py` defines:

- `AIProviderResult` — bounded output carrying `kind`, `confidence`, `provenance`, `provider_id`, and `model_id`;
- `AIProvider` — minimal provider protocol;
- `AIProviderRegistry` — explicit provider registration and fail-closed routing;
- `BaselineRecommendationProvider` — deterministic local implementation preserving the existing baseline recommendation semantics.

Confidence remains evidence strength rather than truth. Provenance is mandatory. Provider selection is explicit and unknown providers fail closed.

## Security boundary

AI output remains observational. The abstraction does not authorize requests, mutate security state, execute game actions, or grant privileges. External providers can be added behind the same contract later without changing those boundaries.

The HTTP recommendation endpoint is intentionally not rewired in this increment; endpoint integration and provider-specific adapters require separate evidence and regression coverage.
