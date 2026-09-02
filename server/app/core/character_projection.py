"""Project character.* game events into the characters store (issue #107 Phase 2)."""

from __future__ import annotations

from typing import Any

# Event types that update the authoritative character projection.
CHARACTER_PROJECT_TYPES = frozenset(
    {
        "character.snapshot",
        "character.upsert",
        "character.state",
    }
)


def character_projection_from_event(user_id: str, event: dict[str, Any]) -> dict[str, Any] | None:
    """Build an upsert payload from a game event, or None if not projectable.

    Required payload fields: game_id, external_id, name.
    Optional: version, state_json | state, remaining keys folded into state_json.
    Invalid payloads return None (event still accepted; projection skipped).
    """
    if event.get("type") not in CHARACTER_PROJECT_TYPES:
        return None
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None
    game_id = payload.get("game_id")
    external_id = payload.get("external_id")
    name = payload.get("name")
    if not game_id or not external_id or not name:
        return None
    state: dict[str, Any]
    if isinstance(payload.get("state_json"), dict):
        state = dict(payload["state_json"])
    elif isinstance(payload.get("state"), dict):
        state = dict(payload["state"])
    else:
        skip = {"game_id", "external_id", "name", "version", "state", "state_json"}
        state = {k: v for k, v in payload.items() if k not in skip}
    try:
        version = int(payload.get("version", 0))
    except (TypeError, ValueError):
        version = 0
    return {
        "user_id": user_id,
        "game_id": str(game_id),
        "external_id": str(external_id),
        "name": str(name),
        "version": version,
        "state_json": state,
    }


def apply_character_projections(store: Any, user_id: str, events: list[dict[str, Any]]) -> int:
    """Upsert character projections for projectable events. Returns count applied."""
    applied = 0
    for event in events:
        item = character_projection_from_event(user_id, event)
        if item is None:
            continue
        store.upsert_character(item)
        applied += 1
    return applied
