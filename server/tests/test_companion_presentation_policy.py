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



@pytest.mark.parametrize(
    ("provider_id", "model_id"),
    [
        ("", "model"),
        ("   ", "model"),
        ("x" * 129, "model"),
        ("provider", ""),
        ("provider", "x" * 129),
    ],
)
def test_recommendation_metadata_rejects_invalid_provider_and_model_ids(provider_id, model_id):
    with pytest.raises(ValueError):
        validate_recommendation_metadata(
            provider_id=provider_id,
            model_id=model_id,
            provenance=(),
            confidence=None,
        )


@pytest.mark.parametrize(
    "provenance",
    [
        tuple(str(index) for index in range(21)),
        ("",),
        ("x" * 257,),
    ],
)
def test_recommendation_metadata_rejects_unbounded_provenance(provenance):
    with pytest.raises(ValueError):
        validate_recommendation_metadata(
            provider_id=None,
            model_id=None,
            provenance=provenance,
            confidence=None,
        )


def test_recommendation_metadata_accepts_optional_identity_and_confidence_boundaries():
    low = validate_recommendation_metadata(
        provider_id=None,
        model_id=None,
        provenance=(),
        confidence=0.0,
    )
    high = validate_recommendation_metadata(
        provider_id="provider",
        model_id="model",
        provenance=("source",),
        confidence=1.0,
    )
    assert low.confidence == 0.0
    assert high.confidence == 1.0

    with pytest.raises(ValueError):
        validate_recommendation_metadata(
            provider_id=None,
            model_id=None,
            provenance=(),
            confidence=-0.01,
        )
