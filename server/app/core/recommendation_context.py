from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .unified_game_state import UGSState

_MAX_TARGETS = 8
_MAX_EVENTS = 16
_MAX_TEXT = 128


def recommendation_context(state: UGSState) -> Mapping[str, Any]:
    """Project validated UGS into a bounded, recommendation-safe context.

    Only normalized state metadata is exposed. Raw adapter payloads are not
    copied into the recommendation context.
    """
    player = None
    if state.player is not None:
        player = {
            "id": state.player.id,
            "realm": state.player.realm,
            "server": state.player.server,
            "class": state.player.class_,
            "spec": state.player.spec,
            "level": state.player.level,
            "combat_state": state.player.combat_state.value,
            "alive": state.player.alive,
        }

    targets = [
        {
            "id": target.id,
            "type": target.type,
            "hostility": target.hostility,
            "level": target.level,
        }
        for target in state.targets[:_MAX_TARGETS]
    ]

    events = [
        {
            "event_type": event.event_type[:_MAX_TEXT],
            "sequence": event.sequence,
            "data_quality": event.data_quality.value,
        }
        for event in state.events[:_MAX_EVENTS]
    ]

    return {
        "schema_version": state.schema_version,
        "state_id": state.state_id,
        "session_id": state.session_id,
        "sequence": state.sequence,
        "source": {
            "adapter_id": state.source.adapter_id,
            "profile": state.source.profile,
        },
        "data_quality": state.data_quality.value,
        "missing_signals": list(state.missing_signals[:_MAX_EVENTS]),
        "player": player,
        "targets": targets,
        "events": events,
        "provenance": list(state.provenance[:_MAX_EVENTS]),
    }
