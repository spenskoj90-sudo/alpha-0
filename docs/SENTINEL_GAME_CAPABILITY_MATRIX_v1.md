# SENTINEL — Game Capability Matrix v1

**Status:** DRAFT FOR OWNER REVIEW  
**Date:** 2026-09-03  
**Scope:** WoW Retail / WoW Legacy 3.3.5a / Private-server profile (WoWCircle reference)  
**Purpose:** define what SENTINEL may observe, infer, display, request and execute at each integration boundary without assuming identical APIs.

> Capability status is an engineering classification, not a claim that a particular server currently permits every capability. `UNVERIFIED` requires validation against the exact client/server build.

## 1. Status vocabulary

| Status | Meaning |
|---|---|
| AVAILABLE | Supported by the integration contract and validated for the target build/environment. |
| LIMITED | Possible, but only for a subset of units/events/data or under restrictions. |
| UNAVAILABLE | Not exposed through the permitted integration boundary. |
| UNVERIFIED | Plausible or historically available, but not yet validated on the exact target build. |

## 2. Core rule

SENTINEL never promotes a capability to `AVAILABLE` merely because another WoW generation exposes a similarly named API. Capability, data quality and authorization are separate concerns.

```text
Game/Client/Server → Adapter → Capability Profile → Unified Game State → Core
Capability available ≠ action authorized
```

## 3. High-level matrix

| Capability | Retail | Legacy 3.3.5a | Private/WoWCircle | Priority |
|---|---|---|---|---|
| Client/version detection | AVAILABLE | AVAILABLE | UNVERIFIED | P0 |
| Player state | AVAILABLE | AVAILABLE | UNVERIFIED | P0 |
| Target state | LIMITED / build-dependent | UNVERIFIED | UNVERIFIED | P0 |
| Combat events | LIMITED / build-dependent | UNVERIFIED | UNVERIFIED | P0 |
| Resources | LIMITED / build-dependent | UNVERIFIED | UNVERIFIED | P0 |
| Cooldowns | LIMITED / build-dependent | UNVERIFIED | UNVERIFIED | P0 |
| Auras | LIMITED / build-dependent | UNVERIFIED | UNVERIFIED | P0 |
| Threat | LIMITED / derived | UNVERIFIED | UNVERIFIED | P1 |
| Party/raid | LIMITED / build-dependent | UNVERIFIED | UNVERIFIED | P1 |
| Boss/encounter context | LIMITED / build-dependent | UNVERIFIED | UNVERIFIED | P1 |
| Position/environment | LIMITED | UNVERIFIED | UNVERIFIED | P1 |
| Chat/context | AVAILABLE / build-dependent | UNVERIFIED | UNVERIFIED | P2 |
| Overlay | AVAILABLE | AVAILABLE | UNVERIFIED | P0 |
| Voice bridge | Companion-level | Companion-level | Companion-level | P2 |
| Command bridge | LIMITED / policy-gated | UNVERIFIED | UNVERIFIED | P1 |
| Direct gameplay automation | Restricted | Environment-dependent | Environment-dependent | Not MVP |

## 4. Retail

Retail is the most restrictive and fast-changing target. Current WoW API security documentation distinguishes protected APIs, hardware-event restrictions, combat restrictions, secure frames and taint; recent 12.x changes further restrict some combat information. Therefore the Retail adapter must discover capabilities at runtime and expose data quality instead of assuming legacy addon behavior.

P0 target: player/basic target state, permitted combat signals, resources/cooldowns/auras where exposed, overlay, local aggregation, event sequencing and capability reporting.

P1 target: group/raid context, threat/context, richer encounter state, replay capture and explanations.

Automation is not assumed to be available to ordinary addon code. SENTINEL must not bypass protected APIs or secure-execution boundaries.

## 5. Legacy 3.3.5a

Legacy is a separate adapter contract. It may expose a materially different addon surface, but exact availability remains `UNVERIFIED` until tested on the exact 3.3.5a client/build used by the target environment.

P0 target: player/target state, combat events, resources, cooldowns, auras, basic group state, overlay and normalized event emission.

P1 target: threat, encounter/boss signals, richer unit context, replay fixtures.

P2 target: voice commands, personalization and environment-specific extensions.

## 6. Private server / WoWCircle

WoWCircle is a first-class validation target, not a universal assumption. The profile must detect client build, server identity, server extensions (if any), addon API behavior, event availability and unit-data availability before publishing capabilities.

Initial profile is intentionally conservative:

```text
client = 3.3.5a (expected; validate)
server = WoWCircle
combat_events = UNVERIFIED
target_state = UNVERIFIED
auras = UNVERIFIED
cooldowns = UNVERIFIED
resources = UNVERIFIED
threat = UNVERIFIED
overlay = UNVERIFIED
command_bridge = UNVERIFIED
action_execution = UNVERIFIED
```

No server-specific behavior may leak into the universal Core model.

## 7. Unified state fields

### Player

```text
id, name, realm/server, class/spec?, level?, health, health_max,
power[], position?, combat_state, alive
```

### Target

```text
id, name, type, health, health_max, hostility, level?,
position?, aura_summary?
```

### Resource

```text
type, current, maximum, regen?, timestamp
```

### Cooldown

```text
ability_id, available, start, duration, remaining,
charges_current?, charges_maximum?
```

### Aura

```text
id, source?, type, stacks?, duration?, remaining?,
is_helpful?, is_harmful?
```

Missing data is represented as unknown/unavailable, never guessed.

## 8. Canonical event envelope

```text
event_id
schema_version
occurred_at
sequence
source
actor
subject
event_type
payload
data_quality
provenance
```

The adapter maps source-specific events to this envelope. AI reasoning does not belong in the adapter.

## 9. Action matrix

| Action | Retail | Legacy | Private | Default policy |
|---|---|---|---|---|
| Overlay | AVAILABLE | AVAILABLE | UNVERIFIED | Allow |
| Recommendation | AVAILABLE | AVAILABLE | UNVERIFIED | Allow |
| Voice response | Companion | Companion | Companion | Allow |
| UI affordance/highlight | Available within UI limits | Available | UNVERIFIED | Allow |
| User-clicked permitted action | Environment-dependent | Environment-dependent | Environment-dependent | Confirm/allow only when permitted |
| Automatic targeting | Restricted | Environment-dependent | Environment-dependent | Deny by default |
| Automatic spell casting | Restricted | Environment-dependent | Environment-dependent | Deny by default |
| Autonomous combat | Not MVP | Not MVP | Not MVP | Deny |
| Memory/process manipulation | Not supported | Not supported | Not supported | Deny |
| Security bypass | Never | Never | Never | Deny |

## 10. Capability negotiation

```text
1. Detect client/build/server.
2. Load exact or family profile.
3. Probe only permitted APIs/features.
4. Validate expected events.
5. Publish capability profile.
6. Start state/event pipeline.
7. Downgrade capability on runtime failure.
```

Capabilities may change during a session; the Core must tolerate transitions.

## 11. Fallback hierarchy

```text
Exact build profile
  ↓
Validated family profile
  ↓
Generic compatible profile
  ↓
Minimal telemetry
  ↓
Offline/local-only
```

Fallback must never silently claim unavailable data.

## 12. Data quality

```text
data_quality = HIGH | MEDIUM | LOW | UNKNOWN
missing_signals[]
source[]
observed_at
ingested_at
```

Recommendations inherit the quality and provenance of their input state.

## 13. First vertical slice

```text
WoW client
  ↓
Adapter
  ↓
Player + target + combat subset
  ↓
Unified Game State v1
  ↓
State Engine
  ↓
Rules/recommendation engine
  ↓
Confidence + provenance
  ↓
Companion
  ↓
SENTINEL Overlay
```

Acceptance evidence: exact client/build, capability profile, normalized events, state projection, recommendation, confidence/provenance, overlay result and a replay fixture that reproduces the result without the live game.

## 14. Test matrix

| Test | Required evidence |
|---|---|
| Adapter unit | source → normalized mapping |
| Contract | schema/version compatibility |
| Capability | correct status reporting |
| Replay | deterministic reprocessing |
| Simulation | synthetic combat/state scenarios |
| Security | adapter cannot bypass Core authorization |
| Failure | safe degradation on missing API/events/network |
| Performance | latency budget measurements |
| Compatibility | exact client/build profile |
| Human acceptance | real target environment |

## 15. Open validation items

1. Exact Retail release-build capability surface.
2. Exact 3.3.5a client/API used for the reference private-server target.
3. WoWCircle-specific addon behavior/extensions.
4. Combat-event coverage per environment.
5. Target/party/threat/aura visibility per environment.
6. Permitted action/secure-template behavior per environment.
7. Real Adapter → Companion → Core latency.
8. Any private-server API deviations.

## 16. Decision

**APPROVED direction:** SENTINEL Core is built against universal capability/state contracts rather than one WoW API.

**Evidence rule:** only exact-environment evidence can promote `UNVERIFIED` to `AVAILABLE`.

**WoWCircle rule:** first-class validation target; never a universal Core assumption.

**Security rule:** current WoW protected/taint restrictions are treated as product constraints, not obstacles to bypass.
