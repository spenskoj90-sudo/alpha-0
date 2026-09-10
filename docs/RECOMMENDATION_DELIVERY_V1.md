# Recommendation Delivery v1

## Purpose

This increment adds a presentation-ready boundary between provider-neutral recommendation orchestration and API/UI delivery.

## Contract

`RecommendationDelivery` accepts already bounded context and delegates provider selection to `RecommendationEngine`. It returns bounded recommendation text together with confidence, provenance, provider identity and model identity.

## Safety boundary

The delivery layer is observational only. It does not authorize actions, execute actions, access credentials, persist game/chat/user data, or perform network I/O.

Unknown providers fail closed through the existing provider registry contract.

## Evidence boundary

This increment establishes the delivery contract and regression coverage. It does not claim endpoint integration, live external-provider inference, or production recommendation quality.
