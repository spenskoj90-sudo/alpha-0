# SENTINEL Recommendation Service v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Provide a bounded application seam that joins `RecommendationDelivery` to the public `RecommendationResponse` model.

## Contract

- Context remains caller-supplied and bounded by the existing request model.
- Provider selection is optional and remains owned by `RecommendationDelivery` / `RecommendationEngine`.
- Provider/model identity, confidence and provenance are preserved.
- The service performs no authorization, persistence, action execution or network I/O.
- The existing API endpoint remains the authorization boundary; this seam does not replace it.

## Evidence boundary

This is an application composition seam. It does not claim external-provider inference or production recommendation quality.
