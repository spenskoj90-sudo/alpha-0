# SENTINEL — Unified Game State v1

**Status:** IMPLEMENTATION CONTRACT
**Version:** 1.0

## 1. Purpose

Unified Game State (UGS) is the game-independent semantic state consumed by Core. It contains observations and explicitly derived metadata; it never pretends that inferred values are authoritative game facts.

## 2. Top-level contract

```json
{
  "schema_version": "1.0",
  "state_id": "opaque-id",
  "session_id": "opaque-id",
  "sequence": 123,
  "observed_at": "RFC3339 timestamp",
  "ingested_at": "RFC3339 timestamp",
  "source": {"adapter_id": "wow-retail", "profile": "retail-build-x"},
  "capabilities": {},
  "player": {},
  "targets": [],
  "group": {},
  "combat": {},
  "resources": [],
  "abilities": [],
  "cooldowns": [],
  "auras": [],
  "threats": [],
  "environment": {},
  "events": [],
  "data_quality": "HIGH",
  "missing_signals": [],
  "provenance": []
}
```

## 3. Semantics

- `schema_version` is the UGS contract version.
- `sequence` is monotonic within a source session when ordering is available.
- `observed_at` is the latest source-observation timestamp represented by the state.
- `ingested_at` is Core receipt time and must never replace `observed_at`.
- `source` identifies the adapter/profile, not a trusted authorization principal.
- `capabilities` records what the adapter says is currently observable; Core still applies its own policy.
- `data_quality` summarizes evidence quality for the snapshot.
- `missing_signals` explicitly records expected-but-unavailable data.
- `provenance` identifies contributing event/fixture identifiers.

## 4. Data-quality rules

Allowed values:

`HIGH | MEDIUM | LOW | UNKNOWN`

A derived field cannot have higher evidence quality than its inputs. If an authoritative observation is unavailable, Core must preserve `unknown`/missing state rather than inventing a value.

## 5. Entity contracts

### Player

```json
{
  "id": "opaque-id",
  "name": "optional display name",
  "realm": "optional",
  "server": "optional",
  "class": "optional",
  "spec": "optional",
  "level": "optional",
  "health": {"current": 0, "maximum": 0},
  "power": [{"type": "mana", "current": 0, "maximum": 0}],
  "position": {"x": 0, "y": 0, "z": 0, "map": "optional"},
  "combat_state": "UNKNOWN",
  "alive": null
}
```

### Target

```json
{
  "id": "opaque-id",
  "name": "optional",
  "type": "player|npc|object|unknown",
  "health": {"current": 0, "maximum": 0},
  "hostility": "friendly|neutral|hostile|unknown",
  "level": null,
  "position": null,
  "aura_summary": []
}
```

### Resource

```json
{
  "type": "mana|energy|rage|other",
  "current": 0,
  "maximum": 0,
  "regen": null,
  "observed_at": "timestamp"
}
```

### Ability/cooldown

```json
{
  "ability_id": "opaque-or-game-id",
  "available": null,
  "start": null,
  "duration": null,
  "remaining": null,
  "charges_current": null,
  "charges_maximum": null
}
```

### Aura

```json
{
  "id": "opaque-or-game-id",
  "source": null,
  "type": "buff|debuff|unknown",
  "stacks": null,
  "duration": null,
  "remaining": null,
  "is_helpful": null,
  "is_harmful": null
}
```

## 6. Combat and environment

Combat state is semantic and conservative:

```text
UNKNOWN | OUT_OF_COMBAT | IN_COMBAT
```

Environment SHOULD contain only facts needed by Core, such as client family/version evidence, map/instance identifier, encounter identifier, and latency/transport health where available. Raw API objects and arbitrary server-specific fields do not belong in UGS.

## 7. Events inside state

`events` is a bounded recent-event window, not an unbounded event log. Durable history belongs to the event/replay subsystem.

Each event follows the Game Adapter Contract v1 envelope. Core may use event provenance to explain derived results.

## 8. Derived state

Derived fields MUST be explicitly distinguishable from observations. Recommended metadata:

```json
{
  "value": {},
  "kind": "observed|derived",
  "confidence": 0.0,
  "provenance": ["event-id"]
}
```

A recommendation is never part of authoritative UGS; recommendations are outputs of the intelligence layer that consume UGS.

## 9. Capability interaction

Core MUST check capability status before treating a field as reliable. For example, an unavailable target-health capability means target health is unknown, not zero.

Capability changes create a new state sequence and may invalidate derived values that depended on the lost signal.

## 10. Ordering and idempotency

Core consumers SHOULD reject duplicate `(session_id, sequence)` state updates when the source guarantees monotonic sequencing. If a source cannot guarantee ordering, the state must carry timestamps and provenance and consumers must tolerate reordering.

The contract does not require global ordering across adapters.

## 11. Privacy

The canonical state must minimize personal data. Display names, chat content, social graph information and raw payloads are optional and must not be persisted or emitted to telemetry unless covered by an explicit privacy/telemetry contract.

Opaque identifiers are preferred for machine processing.

## 12. Compatibility

UGS is independently versioned from adapters and Core. Consumers MUST reject unsupported major versions and MAY negotiate supported minor versions.

A compatibility handshake includes:

```text
UGS schema version
Adapter contract version
Core protocol version
Capability profile version
```

## 13. Failure behavior

If an adapter disconnects, Core keeps the last state only for a bounded freshness window. After the freshness deadline, stale fields are marked unknown and capability status is downgraded. No stale state may silently authorize an action.

If state validation fails, reject the affected update and retain the last known-good state subject to the same freshness rules.

## 14. Test requirements

UGS implementations require:

- schema validation;
- backward/forward compatibility fixtures;
- missing-field tests;
- data-quality propagation tests;
- capability downgrade tests;
- duplicate/out-of-order tests;
- stale-state expiry tests;
- privacy/redaction tests;
- deterministic replay fixtures;
- security tests proving UGS cannot authorize actions by itself.

## 15. First vertical slice

The initial implementation should cover only:

`session → player → target → combat subset → capability profile → normalized events → UGS → deterministic replay`

Expansion to group/threat/encounter/position/voice/action data follows only after exact-environment evidence and contract tests exist.
