# Command Center Recommendation Panel v1

## Purpose

Expose the provider-neutral recommendation contract in the existing Next.js Command Center without turning recommendations into authoritative actions.

## Presentation contract

The panel displays:

- recommendation kind;
- confidence as a bounded percentage;
- recommendation text;
- provider identity;
- model identity;
- provenance;
- an explicit observational-only boundary.

The baseline panel uses the existing deterministic `sentinel-core/context-baseline-v1` identity until live API delivery is integrated.

## Safety boundary

The UI does not execute game actions, grant authorization, access credentials, or infer capabilities from presentation state. Recommendation output remains informational and non-authoritative.

## Evidence boundary

This increment establishes the user-facing visualization contract. It does not claim live recommendation API wiring, production model-provider inference, or real-device visual acceptance.
