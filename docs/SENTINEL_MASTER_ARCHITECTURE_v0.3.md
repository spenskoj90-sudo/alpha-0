# SENTINEL — Master Architecture v0.3

**Status:** APPROVED FOUNDATION / LIVING ARCHITECTURE  
**Date:** 2026-09-03  
**Project:** SENTINEL / ALPHA-0  
**Canonical product repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  

> This document defines the target architecture direction. It does not authorize implementation of every future capability. Requirements are classified as MVP, Phase 2, Platform, or Open/To Validate.

## 1. Product definition

SENTINEL is a **game-agnostic AI gaming intelligence and interaction platform**. It is not a WoW-only addon and not merely a chatbot. The platform observes available game state, normalizes it, analyzes context in real time, provides recommendations and warnings, exposes overlay/dashboard/voice interaction, and supports policy-controlled actions where the target environment permits them.

The original product inspiration was WoWByster. SENTINEL is the independent expansion of that inspiration into a multi-game, extensible platform with a universal intelligence layer.

### Confirmed product capabilities

- Real-time observation of player/game state.
- Real-time analysis and contextual reasoning.
- Contextual recommendations, guidance and warnings.
- Dedicated SENTINEL UI / overlay.
- Target, threat, cooldown and resource awareness where the game integration exposes the relevant data.
- Voice input and output.
- Player commands and conversational interaction.
- Policy-controlled automation where technically and contractually permitted.
- Support for multiple games and multiple client generations.
- Support for private-server environments as first-class integration targets where technically feasible and permitted.

## 2. Architecture principles

1. **Core is game-agnostic.** Game-specific knowledge belongs in adapters, profiles and capability definitions.
2. **New game = adapter, not Core rewrite.**
3. **New feature = module/service whenever practical, not game-specific branching in Core.**
4. **Game facts are authoritative at the game boundary; derived intelligence is not game truth.**
5. **Adapters emit facts/events and are not trusted writers of authoritative server state.**
6. **Authorization is server-authoritative and default-deny.**
7. **AI has no authorization authority.** AI produces fact/inference/recommendation outputs with confidence and provenance.
8. **Automation is policy-controlled.** Capability does not imply permission.
9. **Real-time paths have explicit latency budgets.**
10. **The system remains useful in degraded/offline operation where safe and meaningful.**
11. **Every important architecture decision is documented and versioned.**
12. **The architecture must remain replaceable at the AI provider, game adapter and deployment layers.**

## 3. Target logical architecture

```text
                         SENTINEL PLATFORM
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
 GAME INTEGRATION          INTELLIGENCE           PLAYER EXPERIENCE
        |                       |                       |
   Adapter Layer            Core Engine          Overlay / UI
   Capability Model         State Engine          Dashboard
   Normalizer               Context Engine        Voice
   Event Stream             Reasoning             Commands
        |                    Recommendations       Personalization
        |                    Confidence
        |                    Policy
        +-----------------------+-----------------------+
                                |
                    LOCAL / CLOUD FABRIC
                                |
             +------------------+------------------+
             |                  |                  |
             v                  v                  v
        Companion           FastAPI Core        PostgreSQL
             |
        Local cache
        Local queue
        Overlay
        Game bridge
        Local kill switch

      Replay + Simulation + Observability + Security span all layers
```

## 4. Core domains

The existing security-first modular-monolith foundation remains the starting point. Current repository architecture already separates Identity, Authentication, Authorization, Entitlement, Billing, Game State, Knowledge, Event Processing, Audit and Telemetry, with AI recommendation-only and adapters emitting events. See `docs/ARCHITECTURE_V4.md` and `docs/SENTINEL_CURRENT_STATE.md`.

Target additions/clarifications for the game-intelligence product layer:

- Game Adapter Registry
- Capability Registry
- Unified Game State contract
- Real-time State Engine
- Context Engine
- Recommendation Engine
- Confidence/Provenance Engine
- Policy Engine
- Action/Automation Gateway
- Event Replay subsystem
- Game Simulation subsystem
- AI Provider abstraction and routing
- Local Companion protocol

## 5. Game Adapter Platform

A Game Adapter translates a specific game/client/server environment into the universal SENTINEL contracts.

```text
Game / Client / Server
        |
        v
Adapter
        |
        +--> Detection / Version
        +--> Capability Discovery
        +--> Normalization
        +--> Event Extraction
        +--> Local Integration
        |
        v
Unified Game State / Events
```

Adapters MUST NOT embed AI reasoning or authorization decisions.

### Versioning

Adapters are versioned independently from Core. A game family may contain multiple client adapters:

```text
WoW Adapter Family
  +-- Retail
  +-- Classic / modern variants
  +-- Legacy 3.3.5a
  +-- Other legacy clients
  +-- Private-server profiles
```

A private server profile may extend a client adapter when server-specific mechanics or integration facilities exist. Server identity must not leak into the universal Core model.

### WoW / private-server strategy

WoW is the reference integration family. WoWCircle is a reference private-server profile, especially useful for validating legacy 3.3.5a integration. The design must not assume that all WoW clients expose the same API or data.

Modern WoW restrictions, legacy API differences and private-server extensions are handled by capability discovery rather than hard-coded Core assumptions. No adapter may bypass client security controls or rely on undocumented access as a product requirement.

## 6. Capability model

Every integration exposes a capability profile:

```text
AVAILABLE
LIMITED
UNAVAILABLE
UNVERIFIED
```

Capabilities may include:

- player state
- target state
- party/raid state
- combat state/events
- auras
- cooldowns
- resources
- threats
- environment
- chat
- overlay
- voice bridge
- command bridge
- action execution

Core MUST check capability status before depending on a signal.

Capability != authorization. A technically available action can still be denied by Policy Engine.

## 7. Unified Game State

The Core consumes a normalized, game-independent model.

```text
GameState
  +-- session
  +-- player
  +-- targets
  +-- party / group
  +-- combat
  +-- resources
  +-- abilities
  +-- cooldowns
  +-- threats
  +-- environment
  +-- events
  +-- data_quality
  +-- timestamp / sequence
  +-- source / provenance
```

The game remains authoritative for game facts. SENTINEL may derive state, predictions and recommendations but must label derived data accordingly.

## 8. Real-time intelligence

Processing is divided by latency class:

- **L0:** local immediate rendering/safety controls.
- **L1:** local real-time state processing and low-latency guidance.
- **L2:** cloud or heavier reasoning where latency permits.
- **L3:** asynchronous/post-game analytics and deep analysis.

Every latency-sensitive feature receives a measurable budget before implementation.

## 9. Local Companion

The Companion is the trust boundary between the user's machine/game and cloud services.

Responsibilities:

- game/client detection;
- adapter hosting or bridge;
- local queue/cache;
- overlay/UI integration;
- voice I/O;
- low-latency local processing;
- secure Core communication;
- local kill switch;
- health/watchdog/recovery.

The Companion is not the authorization source of truth.

## 10. Player experience

### Overlay

Real-time, low-density information: important state, threat, recommendation, warning, confidence and action affordance.

### Dashboard

History, analytics, configuration, learning, performance and detailed explanations.

### Voice

Two-way interaction:

```text
Player -> command/question -> SENTINEL
SENTINEL -> answer/recommendation/warning -> Player
```

Voice must degrade gracefully if cloud speech/AI services are unavailable.

## 11. Policy and automation

The architecture separates capability, decision and permission:

```text
Capability
   -> AI / Rules Decision
   -> Policy Engine
   -> ALLOW / CONFIRM / DENY
   -> Action Gateway
```

For WoW and other protected environments, the implementation must use permitted integration mechanisms only. SENTINEL does not bypass client security, protected APIs or server rules.

The local kill switch must work without cloud availability and must fail closed.

## 12. AI architecture

AI is behind an abstraction layer:

```text
AI Gateway
  +-- Provider A
  +-- Provider B
  +-- Local model
  +-- Future providers
```

Routing considers:

- latency budget;
- task complexity;
- cost budget;
- privacy mode;
- availability;
- confidence requirements.

AI outputs must carry, where applicable:

- type: fact / inference / recommendation;
- confidence;
- provenance;
- model/provider metadata;
- timestamp;
- input state version.

AI cannot grant access, alter entitlements, authorize privileged operations or independently execute game actions.

## 13. Replay and simulation

All event-driven intelligence should be testable without a live game.

```text
Recorded Game Events
        |
        v
Replay Engine ----> SENTINEL Core
        ^
        |
Game Simulator ---- synthetic scenarios
```

Replay enables regression testing across Core versions. Simulation enables high-volume testing of combat, PvP, threats, resource depletion, missing signals and latency without requiring a live client.

## 14. Confidence and explainability

Recommendations expose confidence and data quality, not hidden chain-of-thought.

Example conceptual output:

```text
recommendation
confidence: 0.91
data_quality: HIGH
factors: [threat_detected, player_state, available_response]
provenance: [game_event_ids]
```

The player can ask why a recommendation was made and receive a concise factor-based explanation.

## 15. Reliability / degraded operation

The system supports:

```text
FULL
  -> DEGRADED
  -> LOCAL-ONLY
  -> OFFLINE
```

Queues are bounded, idempotent and replay-safe. Core and Companion expose health checks. Watchdogs and safe shutdown prevent stale automation or unsafe state from persisting after component failure.

## 16. Security and privacy

Existing hard security invariants remain mandatory:

- server-authoritative authorization;
- default deny / fail closed;
- append-only audit for security-sensitive events;
- replay protection;
- Android Keystore device identity;
- secrets outside source control;
- RLS as defense in depth;
- AI without authority.

New game-platform requirements:

- local/cloud privacy modes;
- explicit telemetry contract;
- data minimization;
- adapter isolation;
- validated command boundary;
- no arbitrary adapter-to-system access;
- no undocumented game-security bypasses.

## 17. Extensibility

### Feature modules

New product capabilities should attach through stable interfaces rather than game-specific Core branches.

### Adapter SDK

Strategic capability. The SDK should allow future first-party and third-party game adapters without exposing Core authority.

### Extension ecosystem

Strategic capability. UI, analytics, voice, coaching and game adapters may eventually become independently installable modules.

These are architectural targets, not MVP commitments.

## 18. Compatibility and updates

Components are independently versioned:

```text
Core API
Companion API
Adapter API
Game Adapter
UI protocol
Event schema
```

Handshake/capability negotiation determines compatibility. Adapter updates must not require a full SENTINEL reinstall when technically avoidable.

Feature flags allow staged rollout and beta features.

## 19. Observability

Every major boundary emits structured telemetry:

- Game Adapter
- Companion
- Core
- AI Gateway
- Voice
- UI
- Database
- Workers

Use correlation IDs, structured logs, metrics, traces and error reporting. Privacy-sensitive game/user data must be scrubbed or excluded according to the telemetry contract.

## 20. Delivery horizons

### MVP — first credible vertical slice

Goal: prove the end-to-end architecture with one real game integration while preserving the universal contracts.

Required:

- SENTINEL Core integration with existing FastAPI/PostgreSQL foundation;
- Game Adapter Registry + Capability Model;
- Unified Game State v1;
- one reference WoW adapter;
- one legacy/private-server validation profile, preferably WoW 3.3.5a/WoWCircle;
- local Companion bridge;
- basic overlay;
- recommendation engine;
- confidence/provenance;
- Policy Engine;
- local kill switch;
- event recording/replay;
- simulation harness;
- baseline observability;
- security and regression tests.

MVP does NOT require every possible WoW client, every automation action, marketplace, third-party SDK or full autonomous gameplay.

### Phase 2 — product depth

- richer WoW Retail/Legacy capability coverage;
- voice end-to-end;
- deeper combat/strategy intelligence where data permits;
- player personalization;
- advanced dashboard/analytics;
- degraded/offline intelligence improvements;
- AI provider routing;
- performance and cost optimization;
- more replay/simulation scenarios;
- additional game adapters.

### Platform — long-term

- public/private Adapter SDK;
- extension ecosystem/marketplace;
- multiple game families;
- third-party adapters;
- pluggable AI/voice providers;
- broader automation providers where permitted;
- enterprise/operator tooling if product direction requires it.

## 21. Current ALPHA-0 gap assessment

Current repository already provides a strong security-first base: Android, FastAPI, Next.js, Electron launcher, WoW addon sources, PostgreSQL persistence, event ingestion, character/game-state projection, server-authoritative authorization and extensive CI/security controls. `docs/SENTINEL_CURRENT_STATE.md` records the current main HEAD as `6eac9bbf88e614bd2584c78f19877739a4bcf9e0` and identifies the existing WoW addon, launcher and game-state domain. The historical handover is explicitly archived and not authoritative.

The principal product-architecture gap is therefore not "build a backend from zero". It is to evolve the existing secure foundation into the full game-intelligence platform described above.

### Highest-priority gaps

1. Formal Game Adapter contract and registry.
2. Formal Capability schema and discovery protocol.
3. Unified Game State v1 contract.
4. Local Companion architecture/protocol.
5. Real-time latency classes and budgets.
6. Policy Engine / Action Gateway boundary.
7. Replay and simulation infrastructure.
8. Confidence/provenance model for intelligence.
9. WoW version/profile capability matrix, including 3.3.5a/private-server profile.
10. Overlay/voice interaction contracts.
11. AI provider abstraction/routing.
12. Privacy/telemetry contract for game data.
13. Adapter and Companion observability.
14. Compatibility/version negotiation.

Existing security, identity, authorization, persistence and CI infrastructure should be reused unless an architecture review proves a better replacement is required.

## 22. Architecture evolution loop

Every significant technology choice follows:

```text
Current decision
 -> alternative discovered
 -> PoC / benchmark
 -> security / compatibility review
 -> cost / latency review
 -> ADR
 -> adopt or reject
```

No new technology is adopted solely because it is newer. Replacements must demonstrate a measurable benefit or remove a material constraint.

## 23. Source-of-truth rules

1. Approved architecture is recorded in version-controlled documentation.
2. Repository `main` is the product source of truth.
3. Architecture decisions receive ADRs when they materially constrain implementation.
4. Chat discussion may propose changes but does not silently change the specification.
5. A requirement is not considered implemented until code, tests and relevant evidence agree.
6. Historical documents are never treated as current state without verification against the exact repository SHA.

## 24. Immediate next implementation sequence

1. Freeze this architecture as the reviewed target on a PR branch.
2. Create `SENTINEL GAME CAPABILITY MATRIX v1`.
3. Create `GAME ADAPTER CONTRACT v1`.
4. Create `UNIFIED GAME STATE v1`.
5. Audit current `wow-addon/`, `launcher/`, `server/` event/state paths against those contracts.
6. Define Companion protocol and latency classes.
7. Build the smallest end-to-end vertical slice.
8. Add replay/simulation before expanding intelligence.
9. Validate WoW 3.3.5a/private-server assumptions using a real compatible environment.
10. Only then expand Retail, additional private-server profiles and other games.

**Status of this document:** architecture target approved by the Human Owner on 2026-09-03; implementation remains subject to the staged review and evidence rules above.
