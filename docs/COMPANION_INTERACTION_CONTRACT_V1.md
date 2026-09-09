# Companion Overlay / Voice Interaction Contract v1

## Purpose

This increment defines a transport-neutral presentation boundary for Companion overlay and voice surfaces. It carries bounded status, recommendation, and alert text without introducing an action protocol.

## Contract

`CompanionPresentation` contains:

- an explicit `OVERLAY` or `VOICE` presentation channel;
- a bounded `STATUS`, `RECOMMENDATION`, or `ALERT` kind;
- text limited to 2,000 characters;
- a correlation identifier for tracing one presentation across surfaces;
- optional confidence in the inclusive range 0..1;
- bounded provenance metadata;
- a per-instance presentation identifier.

`for_channel()` permits the same presentation to be routed to another explicit presentation surface while preserving presentation and correlation identity.

## Security and authority boundary

Presentation is observational and user-facing only. The contract has no command, execution, authorization, credential, or game-manipulation fields. `action_capable` is explicitly false.

The contract does not authenticate peers, authorize actions, synthesize speech, or provide a transport. Those concerns remain owned by their existing security, Companion transport, and future surface-specific implementations.

## Failure and resource discipline

Invalid or unbounded text, confidence, or provenance is rejected at construction time. The contract uses immutable, slotted dataclasses and bounded fields to keep presentation handling deterministic and resource-bounded.

## Scope boundary

This increment does not claim a production overlay renderer, voice provider, microphone ingestion, speech-to-text, text-to-speech, real-device latency evidence, or end-to-end Companion session integration.
