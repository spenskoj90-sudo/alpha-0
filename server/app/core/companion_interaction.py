from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4


class CompanionPresentationChannel(StrEnum):
    OVERLAY = "OVERLAY"
    VOICE = "VOICE"


class CompanionPresentationKind(StrEnum):
    STATUS = "STATUS"
    RECOMMENDATION = "RECOMMENDATION"
    ALERT = "ALERT"


@dataclass(frozen=True, slots=True)
class CompanionPresentation:
    """Bounded, presentation-only content for Companion UI or voice surfaces."""

    channel: CompanionPresentationChannel
    kind: CompanionPresentationKind
    text: str
    correlation_id: UUID
    provenance: tuple[str, ...] = ()
    confidence: float | None = None
    presentation_id: UUID = uuid4()

    def __post_init__(self) -> None:
        if not self.text or len(self.text) > 2000:
            raise ValueError("text must be between 1 and 2000 characters")
        if not 0.0 <= (self.confidence if self.confidence is not None else 0.0) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if len(self.provenance) > 20:
            raise ValueError("provenance must contain at most 20 items")
        if any(not item or len(item) > 256 for item in self.provenance):
            raise ValueError("provenance items must be between 1 and 256 characters")

    @property
    def action_capable(self) -> bool:
        """Presentation messages never authorize or execute actions."""
        return False

    def for_channel(self, channel: CompanionPresentationChannel) -> CompanionPresentation:
        """Return the same bounded content routed to an explicit presentation channel."""
        return CompanionPresentation(
            channel=channel,
            kind=self.kind,
            text=self.text,
            correlation_id=self.correlation_id,
            provenance=self.provenance,
            confidence=self.confidence,
            presentation_id=self.presentation_id,
        )
