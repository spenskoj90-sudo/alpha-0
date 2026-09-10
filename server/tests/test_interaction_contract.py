import pytest
from pydantic import ValidationError

from app.core.interaction_contract import (
    InteractionIntent,
    InteractionMode,
    InteractionSurface,
    is_action_capable,
)


def test_overlay_intent_is_bounded_and_non_actionable() -> None:
    intent = InteractionIntent(
        surface=InteractionSurface.OVERLAY,
        mode=InteractionMode.ACKNOWLEDGE,
        recommendation_id="rec.context-baseline-v1",
    )

    assert intent.surface is InteractionSurface.OVERLAY
    assert intent.mode is InteractionMode.ACKNOWLEDGE
    assert is_action_capable(intent) is False


def test_voice_intent_supports_localized_presentation() -> None:
    intent = InteractionIntent(
        surface=InteractionSurface.VOICE,
        mode=InteractionMode.DISMISS,
        recommendation_id="rec.context-baseline-v1",
        locale="ru-RU",
    )

    assert intent.surface is InteractionSurface.VOICE
    assert intent.locale == "ru-RU"
    assert is_action_capable(intent) is False


def test_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        InteractionIntent(
            surface=InteractionSurface.OVERLAY,
            mode=InteractionMode.OBSERVE,
            recommendation_id="rec.context-baseline-v1",
            execute_action=True,
        )