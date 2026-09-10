from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class InteractionSurface(StrEnum):
    OVERLAY = "OVERLAY"
    VOICE = "VOICE"


class InteractionMode(StrEnum):
    OBSERVE = "OBSERVE"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    DISMISS = "DISMISS"


class InteractionIntent(BaseModel):
    """Bounded user interaction intent; it never authorizes game actions."""

    model_config = ConfigDict(extra="forbid")

    surface: InteractionSurface
    mode: InteractionMode
    recommendation_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    locale: str = Field(default="en", min_length=2, max_length=16, pattern=r"^[A-Za-z0-9-]+$")


def is_action_capable(intent: InteractionIntent) -> bool:
    """Interaction surfaces are presentation-only in v1."""

    return False