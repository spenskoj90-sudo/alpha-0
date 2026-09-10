# SENTINEL Overlay / Voice Interaction Contract v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT  
**Scope:** presentation and bounded user interaction only

## Boundary

The Command Center overlay and Companion voice surface may present a recommendation and accept a bounded user interaction intent. Version 1 does not authorize, schedule, or execute game actions.

## Surfaces

- `OVERLAY` — visual presentation and user acknowledgement/dismissal.
- `VOICE` — voice-oriented presentation and user acknowledgement/dismissal.

## Interaction modes

- `OBSERVE` — display or announce the recommendation without changing state.
- `ACKNOWLEDGE` — record that the user acknowledged the presentation boundary.
- `DISMISS` — dismiss the presentation.

## Safety properties

- Payloads are bounded and reject unknown fields.
- Recommendation identity is an opaque bounded identifier; raw game/chat/user payloads are not part of this contract.
- Locale is bounded to a simple BCP-47-like token shape.
- No interaction intent is action-capable in v1.
- Any future action-capable interaction must cross the existing Policy Engine / Action Gateway boundary rather than extending this presentation contract.

## Evidence boundary

This contract establishes the software boundary and regression behavior. It does not claim voice transcription quality, device audio performance, production remote transport, or autonomous gameplay.