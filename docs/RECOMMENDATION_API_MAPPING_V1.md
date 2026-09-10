# SENTINEL Recommendation API Mapping v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Provide a bounded mapping from `RecommendationDelivery` output to the existing API response model without changing authorization or provider-selection semantics.

## Contract

- Delivery evidence is preserved: kind, text, confidence, provenance, provider identity and model identity.
- The mapper performs no authorization, action execution, persistence or network I/O.
- Empty delivery output remains an empty API recommendation list.
- Provider selection and fail-closed behavior remain owned by `RecommendationDelivery` / `RecommendationEngine`.

## Evidence boundary

This establishes the API serialization seam. It does not claim live external-provider inference or production recommendation quality.
