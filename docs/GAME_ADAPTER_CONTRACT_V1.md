# SENTINEL — Game Adapter Contract v1

**Status:** IMPLEMENTATION CONTRACT
**Version:** 1.0
**Scope:** game/client/server adapters → Companion/Core

## 1. Purpose

A Game Adapter is the only integration boundary allowed to translate game-specific observations into SENTINEL semantic facts and events. The Core must never depend on WoW API names, client-specific object shapes, or private-server assumptions.

The contract is designed around four invariants:

1. facts are separated from inference and recommendations;
2. capability is separated from authorization;
3. unknown data is explicit and never guessed;
4. exact-environment evidence is required before a capability is declared `AVAILABLE`.

## 2. Trust boundary

```text
Game / Client / Server
        ↓
   Game Adapter
        ↓
Capability Profile + Normalized Events
        ↓
 Unified Game State
        ↓
 Core / Rules / AI
        ↓
 Recommendation
        ↓
 Policy Engine
```

Adapters MUST NOT authorize actions, grant entitlements, call privileged Core internals, execute arbitrary OS operations, manipulate game memory/processes, or bypass protected game APIs.

## 3. Adapter identity

Every adapter instance MUST expose:

```json
{
  "adapter_id": "wow-retail",
  "adapter_version": "1.0.0",
  "game_id": "world-of-warcraft",
  "client_family": "retail",
  "client_version": "exact-or-unknown",
  "server_profile": "official-or-unknown",
  "environment_id": "stable-test-identifier",
  "capability_profile_version": "1.0"
}
```

`client_version`, `server_profile`, and `environment_id` must be treated as untrusted observations until validated.

## 4. Capability model

Allowed status values:

- `AVAILABLE` — validated for the exact target environment.
- `LIMITED` — validated but constrained.
- `UNAVAILABLE` — not exposed through the permitted boundary.
- `UNVERIFIED` — plausible but not validated for the exact environment.

Each capability entry MUST include:

```json
{
  "status": "AVAILABLE",
  "evidence_level": "L3",
  "source": ["game_api", "event"],
  "updated_at": "timestamp",
  "constraints": []
}
```

Evidence levels:

- L1: documented/project-claimed;
- L2: reproducible in controlled test/simulation;
- L3: validated in the exact target game/client/server environment.

Only L3 may promote an environment-specific capability to `AVAILABLE`.

## 5. Capability discovery

On startup and after material runtime changes the adapter MUST:

1. detect game/client/server identity where safely observable;
2. select the most specific known profile;
3. probe only permitted APIs/features;
4. register observed event availability;
5. publish capability status and evidence metadata;
6. downgrade capabilities if runtime evidence becomes invalid.

Capability transitions are monotonic only for the current evidence window: a capability may move `AVAILABLE → LIMITED → UNAVAILABLE` when runtime conditions change and may return to a prior state only after fresh validation.

## 6. Normalized event envelope

Every emitted event MUST conform to this semantic shape:

```json
{
  "event_id": "uuid-or-stable-local-id",
  "schema_version": "1.0",
  "occurred_at": "RFC3339 timestamp",
  "sequence": 123,
  "source": {
    "adapter_id": "wow-retail",
    "profile": "retail-build-x"
  },
  "actor": {"id": "opaque-id"},
  "subject": {"id": "opaque-id"},
  "event_type": "player.state.changed",
  "payload": {},
  "data_quality": "HIGH",
  "provenance": ["source-event-id"]
}
```

Required semantics:

- `event_id` is unique within the adapter event domain;
- `sequence` is monotonic per adapter session where the source permits ordering;
- `occurred_at` describes source occurrence, not ingestion time;
- `payload` contains semantic data, not raw API objects;
- `data_quality` is `HIGH | MEDIUM | LOW | UNKNOWN`;
- `provenance` identifies source evidence without exposing unnecessary user/game data.

Missing values are omitted or explicitly represented as unknown according to the Unified Game State contract. They are never inferred merely to satisfy schema completeness.

## 7. Required event families

The v1 adapter contract recognizes these event families:

- `session.started`
- `session.ended`
- `player.state.changed`
- `target.state.changed`
- `group.state.changed`
- `combat.state.changed`
- `resource.changed`
- `ability.cooldown.changed`
- `aura.changed`
- `environment.changed`
- `capability.changed`
- `adapter.health.changed`

An adapter may emit additional versioned event types, but Core consumers must ignore unknown event types safely.

## 8. Snapshot interface

The adapter SHOULD provide a point-in-time snapshot suitable for state reconstruction:

```json
{
  "schema_version": "1.0",
  "captured_at": "timestamp",
  "session_sequence": 123,
  "capabilities": {},
  "state": {},
  "data_quality": "HIGH",
  "provenance": []
}
```

Snapshots are advisory observations. They do not become authoritative server state merely because they originated from an adapter.

## 9. Transport contract

Transport MUST declare one latency class:

| Class | Intended use | Contract |
|---|---|---|
| `interactive` | commands/UI responses | user-visible request/response |
| `near-real-time` | state/event streaming | bounded queue, ordering, reconnect |
| `batch` | analytics/sync | durable retry, idempotency |
| `offline-replay` | fixtures/testing | deterministic input/output |

The adapter must expose queue depth, dropped-event count, reconnect state and last-successful-send timestamp when the selected transport supports those signals.

A slow transport MUST NOT silently be used for a high-frequency state loop. If the selected transport cannot satisfy the required latency class, the adapter must degrade explicitly.

## 10. Failure and degradation

Failures must affect the smallest possible surface.

```text
source unavailable
    ↓
capability downgraded
    ↓
missing signal recorded
    ↓
state remains partially usable
    ↓
recommendation confidence/data quality reduced
```

The adapter MUST NOT fabricate state, retry without bounds, block the Core indefinitely, or turn a transport failure into an authorization decision.

## 11. Security requirements

Adapters MUST:

- use least-privilege access to local resources;
- validate all inbound data before normalization;
- bound payload sizes and queues;
- avoid executable inbound payloads;
- avoid arbitrary command execution;
- preserve provenance;
- fail closed for unsupported actions;
- respect game/client security boundaries.

Adapters MUST NOT:

- read or modify game process memory;
- inject code into the game process;
- bypass protected APIs or secure execution;
- impersonate a privileged Core identity;
- directly mutate authoritative server state.

## 12. Versioning and compatibility

The contract uses semantic versions. Breaking changes increment the major version. Additive optional fields may use a minor version. Bug-compatible clarifications use a patch version.

Handshake MUST exchange:

```text
adapter contract version
adapter version
Core protocol version
capability profile version
supported transport classes
```

If no compatible contract exists, the connection fails closed and reports a machine-readable compatibility error.

## 13. Determinism and replay

For replayable event sources, the adapter MUST preserve enough metadata to reconstruct the semantic event stream without the live game. Replay fixtures MUST pin:

- adapter version;
- contract version;
- capability profile;
- fixture identifier;
- event ordering;
- expected normalized output.

Live-environment acceptance remains separate from replay evidence.

## 14. Observability

Adapter telemetry SHOULD be structured and bounded. Minimum operational signals:

- adapter/session identity (opaque);
- capability profile/version;
- event counts by family;
- dropped events;
- queue depth;
- transport latency by class;
- normalization failures;
- capability transitions;
- reconnect/recovery count.

User identifiers, chat content and raw game payloads must not be emitted unless explicitly covered by the telemetry/privacy contract.

## 15. Action boundary

The adapter may report that an action is technically possible, but it cannot decide that the action is permitted.

```text
Adapter capability
      ↓
Recommendation / requested action
      ↓
Policy Engine
      ↓
ALLOW | CONFIRM | DENY
      ↓
Action Gateway / permitted integration
```

The default for unknown or unverified action capability is `DENY`.

## 16. v1 acceptance tests

A conforming adapter implementation must have tests covering:

1. identity/version detection;
2. capability status and evidence levels;
3. normalized event mapping;
4. missing/unknown fields;
5. sequence/order behavior;
6. capability downgrade;
7. malformed input rejection;
8. bounded queue/backpressure;
9. transport reconnect/degradation;
10. contract-version incompatibility;
11. replay determinism;
12. security boundary: no authorization or arbitrary action execution in adapter code.

## 17. First implementation target

The first SENTINEL adapter should be a conservative WoW adapter that emits only signals demonstrably available in the selected client/build. Initial implementation priority:

1. session/environment identity;
2. player state;
3. target state where permitted;
4. combat state/events where permitted;
5. resources/cooldowns/auras where permitted;
6. capability reporting;
7. normalized event stream;
8. deterministic fixtures for replay.

The adapter is not considered production-capable until exact-environment validation establishes L3 evidence for the intended capability profile.
