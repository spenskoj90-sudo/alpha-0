import pytest

from app.core.companion_presentation_policy import (
    RecommendationPresentationMetadata,
    bound_presentation_text,
    validate_recommendation_metadata,
)


def test_bound_text_normalizes_whitespace_without_truncation():
    assert bound_presentation_text("  hello\n world  ") == "hello world"


def test_bound_text_rejects_empty_and_oversized_content():
    with pytest.raises(ValueError):
        bound_presentation_text("   ")
    with pytest.raises(ValueError):
        bound_presentation_text("x" * 2001)


def test_recommendation_metadata_is_bounded():
    value = validate_recommendation_metadata(
        provider_id="provider",
        model_id="model",
        provenance=("source",),
        confidence=0.5,
    )
    assert isinstance(value, RecommendationPresentationMetadata)


def test_recommendation_metadata_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        validate_recommendation_metadata(
            provider_id="provider", model_id="model", provenance=(), confidence=1.1
        )
