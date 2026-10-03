from app.core.ai_provider import BaselineRecommendationProvider
from app.core.knowledge_engine import KnowledgeEngine
from app.core.models import Recommendation


def test_missing_context_does_not_fabricate_confidence():
    result=BaselineRecommendationProvider().generate({})
    assert result.confidence is None


def test_uncalibrated_inference_confidence_is_unknown():
    for quality in ('high','low','UNKNOWN'):
        result=KnowledgeEngine().build({'data_quality':quality,'events':[{'event_type':'combat'}]})
        assert result.items[0].confidence is None


def test_unknown_confidence_roundtrips_as_null():
    item=Recommendation(kind='recommendation',text='Review evidence.',confidence=None,provenance=['source'])
    assert item.model_dump()['confidence'] is None
