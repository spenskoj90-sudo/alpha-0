# SENTINEL — Reference & Failure Audit v1

**Status:** DRAFT FOR OWNER REVIEW  
**Date:** 2026-09-03  
**Scope:** reference architectures relevant to SENTINEL Game Adapter, Unified Game State, Companion, overlay, recommendation and replay/simulation layers.

## 1. Purpose

This audit extracts useful engineering patterns from comparable projects and, equally importantly, records observed limitations, failure modes and architectural risks. The objective is not to reproduce any reference implementation. The objective is to prevent SENTINEL from inheriting avoidable coupling, fragility, latency, compatibility and evidence-quality problems.

**Rule:** every borrowed pattern must have a corresponding failure analysis and a SENTINEL countermeasure where a material risk exists.

## 2. Evidence discipline

References are evaluated from publicly available project documentation/repositories. A reference implementation is not treated as proof that a capability exists in a target WoW environment. Exact-environment validation remains governed by the Game Capability Matrix.

Evidence levels used by SENTINEL:

```text
L1 — documented/project-claimed behavior
L2 — reproducible in a controlled test/simulation
L3 — validated in the exact target game/client/server environment
```

Only L3 evidence can promote an environment-specific capability to `AVAILABLE`.

## 3. Reference findings

### 3.1 Byster

**Observed strengths**
- Strong environment/profile orientation for WoW 3.3.5a/private-server usage.
- Role-oriented combat logic and configurable rotation behavior.
- Launcher/companion-oriented user workflow.
- Rich combat context such as cooldowns, procs, boss phases and utility.

**Failure / risk lessons**
- Deep coupling to a particular WoW generation and private-server ecosystem creates compatibility risk when the client/API changes.
- Automation-first architecture makes action execution a central dependency rather than an optional capability.
- Environment-specific behavior can become difficult to separate from universal logic if boundaries are not explicit.

**SENTINEL countermeasures**
- Universal Core contracts; all game-specific behavior lives behind adapters and capability profiles.
- Action execution is policy-gated and capability-dependent, not a required output of intelligence.
- Environment-specific extensions must not leak into the canonical Core state model.

### 3.2 Hekili

**Observed strengths**
- Multi-step next-action prediction rather than a single static recommendation.
- Highly configurable priority-based combat reasoning.
- Large body of practical combat-state logic.

**Failure / risk lessons**
- The Retail project ended with the January 2026 Midnight prepatch because Blizzard API direction made it impossible to continue while meeting its design goals.
- This demonstrates that a sophisticated decision engine can become non-viable when it depends directly on a mutable/protected game API surface.

**SENTINEL countermeasures**
- Capability discovery and runtime degradation.
- Data quality and provenance attached to normalized state.
- No assumption that an API name or historical behavior implies current availability.
- Replay/simulation path independent of the live client.

### 3.3 HeroRotation

**Observed strengths**
- Modular rotation implementations.
- Separate main recommendation, situational utility/defensive suggestions and target cycling.
- SimulationCraft APL alignment provides a structured source for priority logic.
- Explicit acknowledgement that simulation-optimal behavior may perform poorly in live situations.

**Failure / risk lessons**
- Recommendation quality is strongly dependent on the quality and applicability of the underlying APL.
- A simulated agent can assume perfect execution and encounter conditions that do not exist for a human player.
- Excessive sequencing can make an otherwise correct priority model behave poorly in-game.

**SENTINEL countermeasures**
- Separate simulation policy from human-assistance policy.
- Include confidence, explanation and applicability/context in recommendations.
- Prefer bounded candidate evaluation over blindly replaying a theoretical sequence.
- Measure live recommendation quality separately from simulation correctness.

### 3.4 Azeroth Companion

**Observed strengths**
- Clean separation between in-game addon and external companion application.
- AI/network work is kept outside the WoW addon sandbox.
- Runtime compatibility layer targets multiple WoW generations.
- Data-only inbound payload design reduces code-injection risk.

**Failure / risk lessons**
- On 3.3.5a, the documented SavedVariables/reload transport introduces seconds of latency and is explicitly a consultation mechanism rather than a real-time stream.
- Retail restrictions create different transport behavior from legacy clients.
- A transport that is acceptable for chat/consultation is unsuitable for a high-frequency state loop.

**SENTINEL countermeasures**
- Companion transport abstraction with explicit latency classes.
- Separate `interactive`, `near-real-time`, `batch`, and `offline/replay` paths.
- Measure end-to-end latency rather than assuming local IPC is fast enough.
- Preserve a degraded mode when only file/clipboard/manual transport is possible.

### 3.5 Wowless

**Observed strengths**
- Headless WoW Lua/FrameXML execution environment intended for addon testing.
- Useful foundation for deterministic addon/API compatibility tests and CI scenarios.

**Failure / risk lessons**
- Wowless itself documents that it is pre-alpha and that addon errors may originate in the emulator rather than the addon.
- A headless interpreter cannot by itself prove behavior in the exact production game/server environment.

**SENTINEL countermeasures**
- Treat emulator/headless results as L2 evidence, never L3.
- Keep exact-environment acceptance tests separate.
- Record test harness version and fixture provenance with compatibility results.

### 3.6 Private-server automation/bot projects

Projects such as CopilotBuddy and AzerothCore playerbot ecosystems demonstrate the breadth possible when the environment is controlled: navigation, profiles, routines, plugins, AI bots and server-side extensions.

**Failure / risk lessons**
- Client attachment, memory/process access and invasive automation are powerful but create high fragility, security and compatibility costs.
- Server-side or modified-client assumptions do not generalize to ordinary retail addon boundaries.
- Large integrated bot stacks can make it difficult to isolate which component is responsible for a failure.

**SENTINEL countermeasures**
- Keep Core independent from invasive client mechanisms.
- Explicitly classify integration boundaries and trust levels.
- Default-deny action policy and no memory/process manipulation or security bypass.
- Component-level observability and replayable evidence.

## 4. Cross-project failure patterns

### F1 — API optimism

**Pattern:** assume a historically available API remains available and semantically equivalent.

**Countermeasure:** runtime capability probe + exact-build profile + data-quality status + fallback.

### F2 — Game-specific logic leaking into Core

**Pattern:** universal engine becomes a collection of WoW assumptions.

**Countermeasure:** adapter-owned normalization; Core consumes semantic contracts only.

### F3 — Intelligence coupled directly to execution

**Pattern:** every recommendation assumes an executable action path.

**Countermeasure:** recommendation and action are separate contracts; Policy Engine is authoritative.

### F4 — Simulation treated as reality

**Pattern:** an optimal APL or emulator result is treated as proof of live correctness.

**Countermeasure:** explicit evidence levels, human acceptance, live-vs-simulation metrics.

### F5 — Transport latency hidden by architecture

**Pattern:** file/reload or other slow transport is accidentally used for high-frequency state.

**Countermeasure:** latency classes, transport negotiation and end-to-end measurement.

### F6 — Single point of compatibility failure

**Pattern:** one client/API version change breaks the entire product.

**Countermeasure:** capability-scoped degradation; core remains operational with partial state.

### F7 — Data without provenance

**Pattern:** inferred or stale data is indistinguishable from authoritative observations.

**Countermeasure:** `data_quality`, `provenance`, `observed_at`, `ingested_at`, missing-signal reporting.

### F8 — Over-sequenced recommendations

**Pattern:** a theoretical sequence is too rigid for human execution or live encounter variance.

**Countermeasure:** candidate ranking, context-aware policy and confidence rather than unconditional sequences.

### F9 — Test-harness false confidence

**Pattern:** passing emulator/mocked tests is treated as production compatibility.

**Countermeasure:** L1/L2/L3 evidence model and exact-environment acceptance gate.

### F10 — Monolithic integration surface

**Pattern:** addon, companion, AI, UI and action execution share uncontrolled assumptions.

**Countermeasure:** explicit contracts between Adapter, State, Intelligence, Companion, Overlay and Policy layers.

## 5. Required SENTINEL architectural controls

The following controls are promoted from lessons learned into architecture requirements:

1. **Capability negotiation is mandatory** before environment-specific behavior is enabled.
2. **Capability status is dynamic** and may downgrade during a session.
3. **Data quality and provenance are first-class state metadata.**
4. **Recommendation is independent from action execution.**
5. **Policy Engine is the final action authority.**
6. **Every transport has a declared latency class.**
7. **Replay and simulation must be able to operate without the live game.**
8. **Simulation/emulation cannot substitute for exact-environment acceptance.**
9. **Game-specific code cannot define the universal Core state schema.**
10. **Fallback must be explicit and must never silently invent missing data.**
11. **Observability must identify source, adapter, capability profile and processing stage.**
12. **Compatibility failures must degrade the smallest possible surface.**
13. **No security/protection boundary is bypassed to recover a capability.**
14. **Reference-project behavior is inspiration/evidence, not an architectural dependency.**

## 6. Architecture consequences

The audit reinforces the following dependency direction:

```text
Exact Game Environment
        ↓
Game Adapter
        ↓
Capability Profile + Evidence
        ↓
Normalized Event / State Contract
        ↓
Unified Game State
        ↓
State Analysis / Rules / AI
        ↓
Recommendation
        ↓
Confidence + Provenance
        ↓
Policy Engine
        ↓
Permitted Action / Overlay / Voice
```

Transport and replay remain orthogonal infrastructure:

```text
Adapter ──→ Companion ──→ Core
   │            │
   └────────→ Replay ←────┘
```

## 7. Reference-to-SENTINEL mapping

| Reference | Adopt | Avoid / mitigate |
|---|---|---|
| Byster | environment profiles, rich combat context, companion workflow | WoW-generation coupling, automation-first dependency |
| Hekili | multi-step prediction, priority reasoning | direct dependency on unstable/protected API surface |
| HeroRotation | modular recommendations, APL concepts, situational actions | treating simulation as guaranteed live behavior |
| Azeroth Companion | addon/companion split, data-only bridge | reload/file transport for real-time workloads |
| Wowless | headless addon testing | treating emulator output as exact-client proof |
| Private-server bot stacks | controlled environment profiles, modular routines | invasive client coupling, monolithic bot assumptions |

## 8. Exit criteria for this audit

Before `Game Adapter Contract v1` is considered ready:

- each major reference has documented strengths and failure modes;
- every material failure mode has a SENTINEL countermeasure or an explicit accepted risk;
- capability/evidence semantics are reflected in the contract;
- transport latency classes are reflected in the contract;
- replay/simulation and exact-environment validation are separate evidence paths;
- action authorization remains outside the Adapter;
- no reference project becomes a runtime dependency without an explicit Owner decision.

## 9. Decision

**Owner-approved direction:** use both successes and failures of comparable projects as architectural input.

**Current conclusion:** SENTINEL should optimize for resilience to API changes, environment variance, transport limitations and evidence uncertainty rather than maximizing immediate feature breadth.

**Next artifact:** `Game Adapter Contract v1`, incorporating the approved Capability Matrix and this Failure Audit.
