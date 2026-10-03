# SENTINEL Knowledge Engine

## Knowledge types

`fact` is directly observed or externally verified. `inference` is derived from one or more facts. `recommendation` is an optional action-oriented suggestion generated from facts/inferences and user context.

AI output is never an authority. It cannot grant entitlement, change authorization, mutate billing, revoke a device, or issue an executable game command.

## Confidence model

Confidence is nullable. Unknown/uncalibrated evidence carries `null`, never a synthetic zero or a fixed probability derived from a quality label. Baseline extraction and generic progression inference have no calibrated estimate and keep confidence unknown. A numeric estimate must have separately justified calibration/provenance; it does not prove truth or grant authority. Missing source time remains unknown.

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
  {"kind":"fact","text":"Character is level 27.","confidence":null,"provenance":["character:27"]},
  {"kind":"inference","text":"Recent activity suggests progression focus.","confidence":null,"provenance":["event:mission_completed","event:inventory_changed"]},
  {"kind":"recommendation","text":"Review the recent inventory change before choosing the next progression step.","confidence":null,"provenance":["inference:progression-focus","preference:risk-low"]}
]
```

The UI presents recommendation text as a suggestion. It does not expose a privileged action endpoint through the AI channel.
