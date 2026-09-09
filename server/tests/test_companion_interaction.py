from uuid import uuid4

import pytest

from app.core.companion_interaction import (
    CompanionPresentation,
    CompanionPresentationChannel,
    CompanionPresentationKind,
)


def test_presentation_is_bounded_and_non_actionable() -> None:
    presentation = CompanionPresentation(
        channel=CompanionPresentationChannel.OVERLAY,
        kind=CompanionPresentationKind.RECOMMENDATION,
        text="Review the latest character events.",
        correlation_id=uuid4(),
        provenance=("sentinel-core:context-baseline",),
        confidence=0.72,
    )

    assert presentation.action_capable is False
    assert presentation.provenance == ("sentinel-core:context-baseline",)
    assert presentation.confidence == 0.72


def test_for_channel_preserves_identity_and_content() -> None:
    presentation = CompanionPresentation(
        channel=CompanionPresentationChannel.OVERLAY,
        kind=CompanionPresentationKind.STATUS,
        text="Companion is active.",
        correlation_id=uuid4(),
    )

    voice = presentation.for_channel(CompanionPresentationChannel.VOICE)

    assert voice.channel is CompanionPresentationChannel.VOICE
    assert voice.presentation_id == presentation.presentation_id
    assert voice.correlation_id == presentation.correlation_id
    assert voice.text == presentation.text


def test_presentation_ids_are_unique_by_default() -> None:
    first = CompanionPresentation(
        channel=CompanionPresentationChannel.OVERLAY,
        kind=CompanionPresentationKind.STATUS,
        text="first",
        correlation_id=uuid4(),
    )
    second = CompanionPresentation(
        channel=CompanionPresentationChannel.OVERLAY,
        kind=CompanionPresentationKind.STATUS,
        text="second",
        correlation_id=uuid4(),
    )

    assert first.presentation_id != second.presentation_id


def test_invalid_bounds_are_rejected() -> None:
    with pytest.raises(ValueError):
        CompanionPresentation(
            channel=CompanionPresentationChannel.OVERLAY,
            kind=CompanionPresentationKind.ALERT,
            text="",
            correlation_id=uuid4(),
        )

    with pytest.raises(ValueError):
        CompanionPresentation(
            channel=CompanionPresentationChannel.VOICE,
            kind=CompanionPresentationKind.ALERT,
            text="alert",
            correlation_id=uuid4(),
            confidence=1.1,
        )

    with pytest.raises(ValueError):
        CompanionPresentation(
            channel=CompanionPresentationChannel.VOICE,
            kind=CompanionPresentationKind.ALERT,
            text="alert",
            correlation_id=uuid4(),
            provenance=("",),
        )
