from __future__ import annotations

from dataclasses import dataclass

MAX_PRESENTATION_TEXT = 2000
MAX_PROVENANCE_ITEMS = 20
MAX_PROVENANCE_ITEM = 256
MAX_PROVIDER_ID = 128
MAX_MODEL_ID = 128


@dataclass(frozen=True, slots=True)
class RecommendationPresentationMetadata:
    provider_id: str | None
    model_id: str | None
    provenance: tuple[str, ...]
    confidence: float | None

    def __post_init__(self) -> None:
        for value, name in ((self.provider_id, "provider_id"), (self.model_id, "model_id")):
            if value is not None and (not value.strip() or len(value) > MAX_PROVIDER_ID):
                raise ValueError(f"{name} must be between 1 and 128 characters")
        if len(self.provenance) > MAX_PROVENANCE_ITEMS:
            raise ValueError("provenance must contain at most 20 items")
        if any(not item or len(item) > MAX_PROVENANCE_ITEM for item in self.provenance):
            raise ValueError("provenance items must be between 1 and 256 characters")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


def bound_presentation_text(text: str) -> str:
    """Normalize presentation text without silently truncating content."""
    normalized = " ".join(text.split())
    if not normalized:
        raise ValueError("presentation text cannot be empty")
    if len(normalized) > MAX_PRESENTATION_TEXT:
        raise ValueError("presentation text exceeds 2000 characters")
    return normalized


def validate_recommendation_metadata(
    *,
    provider_id: str | None,
    model_id: str | None,
    provenance: tuple[str, ...],
    confidence: float | None,
) -> RecommendationPresentationMetadata:
    return RecommendationPresentationMetadata(
        provider_id=provider_id,
        model_id=model_id,
        provenance=provenance,
        confidence=confidence,
    )
