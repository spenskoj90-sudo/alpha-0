# SENTINEL Knowledge Engine

## Knowledge types

`fact` is directly observed or externally verified. `inference` is derived from one or more facts. `recommendation` is an optional action-oriented suggestion generated from facts/inferences and user context.

AI output is never an authority. It cannot grant entitlement, change authorization, mutate billing, revoke a device, or issue an executable game command.

## Confidence model

Every item carries `confidence ∈ [0,1]` and provenance identifiers. Confidence is not truth; it expresses evidence strength. The engine keeps provenance so a recommendation can be traced back to facts and their source events.

Suggested policy:

- 0.90–1.00: strongly evidenced fact
- 0.70–0.89: high-confidence inference
- 0.50–0.69: tentative inference/recommendation
- <0.50: suppress from default user-facing recommendations unless explicitly requested

Confidence should decrease when evidence is stale, contradictory, sparse, or sourced from an untrusted adapter.

## Context Engine example

Input:

```json
{
  "character": {"level": 27, "health": 0.94},
  "recent_events": ["mission_completed", "inventory_changed"],
  "entitlements": ["core"],
  "user_preferences": {"risk": "low"}
}
```

Output:

```json
[
  {"kind":"fact","text":"Character is level 27.","confidence":1.0,"provenance":["character:27"]},
  {"kind":"inference","text":"Recent activity suggests progression focus.","confidence":0.78,"provenance":["event:mission_completed","event:inventory_changed"]},
  {"kind":"recommendation","text":"Review the recent inventory change before choosing the next progression step.","confidence":0.72,"provenance":["inference:progression-focus","preference:risk-low"]}
]
```

The UI presents recommendation text as a suggestion. It does not expose a privileged action endpoint through the AI channel.
