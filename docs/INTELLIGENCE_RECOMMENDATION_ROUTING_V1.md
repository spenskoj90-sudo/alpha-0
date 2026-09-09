# Intelligence Recommendation Routing v1

## Purpose

This increment establishes the first provider-neutral intelligence orchestration seam on top of the AI provider abstraction. It routes bounded normalized context to an explicitly registered provider and returns the provider's bounded result with confidence and provenance intact.

## Contract

`RecommendationEngine` owns provider selection but does not implement model inference. With no explicit provider, it routes to the deterministic `sentinel-core/context-baseline-v1` provider already defined by the AI provider abstraction. An explicit provider identifier is supported for controlled integration and testing.

Unknown providers fail closed with the existing `AI_PROVIDER_NOT_REGISTERED` error. The engine does not invent confidence, provenance, or recommendation text; those remain provider-owned outputs validated by `AIProviderResult`.

## Security boundary

The engine is observational only. It does not authorize or execute game actions, bypass the Policy Engine / Action Gateway, access credentials, perform network I/O, or select an unregistered provider.

## Resource and evidence boundary

The engine passes the already bounded request context to the provider and performs no external calls. The deterministic baseline remains suitable for regression validation without a live AI service. This increment does not claim production model-provider integration or autonomous gameplay.
