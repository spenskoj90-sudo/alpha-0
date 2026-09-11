# Recommendation Endpoint Application v2

This increment connects the existing `/v1/recommendations` surface to the provider-neutral recommendation application seam without changing the server-authoritative authorization boundary.

## Runtime path

1. The existing FastAPI application includes `wow_api` before the legacy recommendation handler in `app.main`.
2. `wow_api` now registers the same `/v1/recommendations` route first, so the application/provider seam is used without duplicating authorization logic.
3. The endpoint calls `RecommendationApplication`, which delegates to `RecommendationService` and `RecommendationDelivery`.
4. Provider identity, model identity, confidence and provenance remain part of the bounded response contract.
5. `X-Recommendation-Provider` is optional; an unknown provider fails closed rather than silently selecting another provider.

## Security boundary

Authorization remains server-authoritative through the existing `knowledge:recommend` policy. This increment introduces no action execution, persistence, provider credentials or external network calls.

The request context remains bounded by the existing `RecommendationRequest` model. A future UGS-backed endpoint can feed the existing `recommendation_context()` projection; this increment does not claim that arbitrary request context is equivalent to validated UGS.

## Companion telemetry boundary

`build_companion_runtime()` now accepts an explicit `persistent_engine` for PostgreSQL telemetry composition. Default construction remains local/bounded, and passing both an explicit telemetry sink and persistent engine is rejected as ambiguous.

No database connection is opened by the builder itself.

## Evidence boundary

The increment does not claim production provider availability, real external AI calls, remote end-to-end latency, or production telemetry delivery. Those remain separate environment-level evidence requirements.
