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

## 2. Architectural rule

SENTINEL must never infer `AVAILABLE` from the existence of a similarly named API on another client generation.

```text
Game/Client/Server
       ↓
Adapter capability discovery
       ↓
Capability profile
       ↓
Unified Game State
       ↓
Core intelligence
```

A capability is separate from permission:

```text
CAPABILITY AVAILABLE
        ≠
ACTION AUTHORIZED
```

The Policy Engine remains the authority for actions.

## 3. High-level matrix

| Capability family | Retail | Legacy 3.3.5a | Private server / WoWCircle | MVP priority |
|---|---|---|---|---|
| Client/version detection | AVAILABLE | AVAILABLE | UNVERIFIED | P0 |
| Player identity/state | AVAILABLE | AVAILABLE | UNVERIFIED | P0 |
| Target state | LIMITED/UNVERIFIED by data surface | AVAILABLE/UNVERIFIED | UNVERIFIED | P0 |
| Combat event stream | LIMITED by current API restrictions | AVAILABLE/UNVERIFIED | UNVERIFIED | P0 |
| Player resources | LIMITED/UNVERIFIED | AVAILABLE/UNVERIFIED | UNVERIFIED | P0 |
| Cooldowns | LIMITED/UNVERIFIED | AVAILABLE/UNVERIFIED | UNVERIFIED | P0 |
| Auras/buffs/debuffs | LIMITED/UNVERIFIED | AVAILABLE/UNVERIFIED | UNVERIFIED | P0 |
| Threat | LIMITED/UNVERIFIED | AVAILABLE/UNVERIFIED | UNVERIFIED | P1 |
| Party/raid state | LIMITED/UNVERIFIED | AVAILABLE/UNVERIFIED | UNVERIFIED | P1 |
| Boss/mechanic state | LIMITED/UNVERIFIED | AVAILABLE/UNVERIFIED | UNVERIFIED | P1 |
| Position/environment | LIMITED/UNVERIFIED | LIMITED/UNVERIFIED | UNVERIFIED | P1 |
| Chat/context | AVAILABLE/UNVERIFIED | AVAILABLE/UNVERIFIED | UNVERIFIED | P2 |
| Overlay | AVAILABLE | AVAILABLE | UNVERIFIED | P0 |
| Voice bridge | Companion-level, not game API | Companion-level, not game API | Companion-level, not game API | P2 |
| Command bridge | LIMITED and policy-gated | LIMITED/UNVERIFIED | UNVERIFIED | P1 |
| Direct gameplay automation | RESTRICTED / generally not product baseline | Environment-dependent | Environment-dependent | Not MVP |

## 4. Retail profile

Current Retail must be treated as the most restrictive and fast-changing integration target.

Current WoW API documentation distinguishes protected APIs, hardware-event restrictions, combat restrictions, secure frames and taint. Recent 12.x changes further restrict access to some combat information. Therefore the Retail adapter must use capability discovery and data-quality reporting rather than assuming legacy addon behavior remains available. citeturn0search0turn0search4turn0search6

### Retail target capabilities

**P0 / target:**
- player identity;
- player basic state;
- target identity/basic state where exposed;
- available combat events/data;
- resources where exposed;
- cooldown information where exposed;
- aura information where exposed;
- overlay rendering;
- local state aggregation;
- event timestamps/sequence;
- capability and data-quality reporting.

**P1:**
- group/raid context;
- threat/context signals where exposed;
- richer encounter state;
- historical/replay capture;
- recommendation explanations.

**Explicit limitation:** Retail automation is not assumed to be directly executable by ordinary addon code. Secure execution and protected API boundaries require human-driven interaction for many actions. SENTINEL must not attempt to bypass those boundaries. citeturn0search4turn0search11

## 5. Legacy 3.3.5a profile

Legacy 3.3.5a is expected to expose a materially different and, in some areas, richer addon surface than modern Retail. However, the exact client build and distribution must be validated before assigning `AVAILABLE`.

### Legacy target capabilities

**P0 / target:**
- player state;
- target state;
- combat log/events;
- resources;
- cooldowns;
- auras;
- basic group state;
- overlay;
- event recording;
- normalized state emission.

**P1:**
- threat;
- encounter/boss signals;
- richer unit context;
- replay/simulation fixtures derived from real sessions.

**P2:**
- voice-driven command interaction;
- advanced player personalization;
- environment-specific extensions.

All entries remain `UNVERIFIED` until validated on an actual 3.3.5a environment.

## 6. Private-server / WoWCircle profile

WoWCircle is a reference target, not a guarantee of API behavior.

The private-server adapter must first detect:

```text
client build
server identity
server API extensions (if any)
addon API behavior
available events
available unit data
```

Then it publishes a capability profile.

### Required private-server states

A server profile may report:

```text
client = 3.3.5a
server = wowcircle
capabilities = {
  combat_events: UNVERIFIED,
  target_state: UNVERIFIED,
  auras: UNVERIFIED,
  cooldowns: UNVERIFIED,
  resources: UNVERIFIED,
  threat: UNVERIFIED,
  overlay: UNVERIFIED,
  command_bridge: UNVERIFIED,
  action_execution: UNVERIFIED
}
```

This is intentionally conservative until the actual environment is tested.

## 7. Detailed capability contract

### 7.1 Player state

Minimum normalized fields:

```text
player.id
player.name
player.realm/server
player.class/spec (if available)
player.level (if available)
player.health
player.health_max
player.power[]
player.position (if available)
player.combat_state
player.alive
```

Missing fields are represented as unavailable/unknown, never guessed.

### 7.2 Target state

```text
target.id
target.name
target.type
target.health
target.health_max
target.hostility
target.level
target.position
target.aura_summary
```

Unit visibility and secret-value restrictions can reduce this profile on Retail.

### 7.3 Combat events

Canonical event envelope:

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

The adapter converts source-specific combat events into canonical events without embedding AI reasoning.

### 7.4 Resources

Normalize resource types rather than assuming one resource model:

```text
resource.type
resource.current
resource.maximum
resource.regen
resource.timestamp
```

### 7.5 Cooldowns

Normalize:

```text
ability.id
ability.available
cooldown.start
cooldown.duration
cooldown.remaining
charges.current
charges.maximum
```

Modern APIs change over time, so the adapter owns version-specific extraction.

### 7.6 Auras

Normalize:

```text
aura.id
aura.source
aura.type
stacks
duration
remaining
is_helpful
is_harmful
```

If the client returns opaque/secret values, the adapter reports reduced data quality rather than fabricating values.

### 7.7 Threat

Threat is a derived integration capability. It may be unavailable even if combat events exist.

The Core must distinguish:

```text
observed threat
estimated threat
unavailable threat
```

### 7.8 Group state

Possible normalized entities:

```text
party.member[]
raid.member[]
role
health
resource
combat_state
distance/position when available
```

No Core feature may require party data unless the capability profile says it is available.

## 8. Action capability matrix

Actions are more restricted than observations.

| Action | Retail | Legacy | Private server | SENTINEL policy |
|---|---|---|---|---|
| Show overlay | AVAILABLE | AVAILABLE | UNVERIFIED | Allow |
| Show recommendation | AVAILABLE | AVAILABLE | UNVERIFIED | Allow |
| Voice response | Companion | Companion | Companion | Allow |
| Highlight UI affordance | AVAILABLE within UI limits | AVAILABLE | UNVERIFIED | Allow |
| User-clicked secure action | Environment/API dependent | Environment/API dependent | Environment dependent | Confirm/allow only when permitted |
| Automatic targeting | Restricted | Environment-dependent | Environment-dependent | Deny by default |
| Automatic spell casting | Restricted | Environment-dependent | Environment-dependent | Deny by default |
| Autonomous combat loop | Not MVP / not baseline | Not MVP | Not MVP | Deny |
| Direct memory/process manipulation | Not a supported integration | Not a supported integration | Not a supported integration | Deny |
| Client security bypass | Never | Never | Never | Deny |

The product can be intelligent without autonomous gameplay. Recommendation and player-controlled interaction remain first-class capabilities.

## 9. Data-quality contract

Every state snapshot and recommendation receives:

```text
data_quality = HIGH | MEDIUM | LOW | UNKNOWN
missing_signals[]
source[]
observed_at
ingested_at
```

This prevents the AI from treating missing Retail data as a fact.

## 10. Capability negotiation

On adapter startup:

```text
1. Detect client/build/server.
2. Load static profile.
3. Probe only permitted APIs/features.
4. Validate expected event streams.
5. Publish capability profile.
6. Start event/state pipeline.
7. Downgrade capabilities on runtime failures.
```

Capabilities can change during a session. Example: entering combat can change what a Retail addon can safely access.

## 11. Adapter fallback hierarchy

```text
Exact build profile
      ↓
Validated family profile
      ↓
Generic compatible profile
      ↓
Minimal telemetry profile
      ↓
Offline/local-only
```

No fallback may silently claim a capability it cannot validate.

## 12. First vertical slice

The first end-to-end slice should deliberately avoid requiring every game feature.

### Slice A — observation → intelligence → overlay

```text
WoW client
   ↓
Adapter
   ↓
Player/target/combat subset
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

Required acceptance evidence:

- exact client/build recorded;
- capability profile emitted;
- normalized events accepted by Core;
- state projection updated;
- recommendation generated from observed state;
- confidence/provenance attached;
- overlay renders the result;
- replay fixture created;
- same fixture reproduces the result without the live game.

## 13. Test matrix

| Test layer | Requirement |
|---|---|
| Adapter unit tests | source → normalized event/state mapping |
| Contract tests | schema/version compatibility |
| Capability tests | correct AVAILABLE/LIMITED/UNAVAILABLE reporting |
| Replay tests | deterministic reprocessing |
| Simulation tests | synthetic combat/state scenarios |
| Security tests | adapter cannot bypass Core authorization |
| Failure tests | missing API/event/connection causes safe degradation |
| Performance tests | latency budgets measured per class |
| Compatibility tests | exact client/build profile |
| Human acceptance | real client/server validation |

## 14. Open validation items

These must remain `UNVERIFIED` until tested against real environments:

1. Exact Retail build capability surface for the release target.
2. Exact 3.3.5a client/addon API used by the reference private-server profile.
3. WoWCircle server-specific addon behavior and any extensions.
4. Exact combat-event coverage available in each target environment.
5. Exact target/party/threat/aura visibility per environment.
6. Exact permitted action/secure-template behavior per environment.
7. Real latency measurements for Adapter → Companion → Core.
8. Whether a given private server changes or extends addon APIs.

## 15. Design decision

**Approved direction:** build the SENTINEL Core against universal capability/state contracts, not against a single WoW API.

**Implementation rule:** a capability is promoted from `UNVERIFIED` to `AVAILABLE` only after exact-environment evidence exists.

**Private-server rule:** WoWCircle is a first-class validation target, but no WoWCircle-specific assumption becomes universal Core behavior.

## 16. External reference note

Modern WoW addon security is an architectural constraint. Current API documentation describes protected APIs, hardware-event requirements, combat restrictions, secure execution and taint; recent 12.x API changes further restrict access to some combat information. These constraints are why SENTINEL's capability model deliberately separates observation, recommendation and action execution. citeturn0search0turn0search4turn0search6
