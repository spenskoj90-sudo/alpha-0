from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.ai_provider import AIProviderRegistry, AIProviderResult, BaselineRecommendationProvider
from app.core.knowledge_engine import KnowledgeEngine, KnowledgeItem, KnowledgeSnapshot


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"text": ""}, "AI_RESULT_TEXT_INVALID"),
        ({"text": "x" * 2001}, "AI_RESULT_TEXT_INVALID"),
        ({"confidence": -0.01}, "AI_RESULT_CONFIDENCE_INVALID"),
        ({"confidence": 1.01}, "AI_RESULT_CONFIDENCE_INVALID"),
        ({"provenance": ()}, "AI_RESULT_PROVENANCE_INVALID"),
        ({"provenance": tuple(str(i) for i in range(21))}, "AI_RESULT_PROVENANCE_INVALID"),
        ({"provenance": ("",)}, "AI_RESULT_PROVENANCE_INVALID"),
        ({"provenance": ("x" * 257,)}, "AI_RESULT_PROVENANCE_INVALID"),
        ({"provider_id": ""}, "AI_RESULT_PROVIDER_INVALID"),
        ({"provider_id": "x" * 129}, "AI_RESULT_PROVIDER_INVALID"),
        ({"model_id": ""}, "AI_RESULT_MODEL_INVALID"),
        ({"model_id": "x" * 129}, "AI_RESULT_MODEL_INVALID"),
    ],
)
def test_ai_provider_result_rejects_unbounded_or_unattributed_output(updates, error: str) -> None:
    values = {
        "kind": "inference",
        "text": "bounded",
        "confidence": 0.5,
        "provenance": ("test:source",),
        "provider_id": "provider",
        "model_id": "model",
    }
    values.update(updates)
    with pytest.raises(ValueError, match=error):
        AIProviderResult(**values)


class StubProvider:
    def __init__(self, provider_id: str, model_id: str = "model") -> None:
        self.provider_id = provider_id
        self.model_id = model_id

    def generate(self, context):
        del context
        return AIProviderResult(
            kind="fact",
            text="ok",
            confidence=1.0,
            provenance=("stub",),
            provider_id=self.provider_id.strip(),
            model_id=self.model_id,
        )


def test_provider_registry_routes_describes_and_fails_closed() -> None:
    first = StubProvider(" alpha ")
    second = StubProvider("beta", "model-b")
    registry = AIProviderRegistry((first,), default_provider_id="alpha")
    registry.register(second)

    assert registry.provider_ids() == ("alpha", "beta")
    assert registry.route() is first
    assert registry.route("beta") is second
    assert registry.describe() == (
        {"provider_id": "alpha", "model_id": "model", "default": True},
        {"provider_id": "beta", "model_id": "model-b", "default": False},
    )

    registry.set_default("beta")
    assert registry.route() is second

    with pytest.raises(ValueError, match="AI_PROVIDER_ALREADY_REGISTERED"):
        registry.register(StubProvider("beta"))
    with pytest.raises(ValueError, match="AI_PROVIDER_ID_REQUIRED"):
        registry.register(StubProvider("   "))
    with pytest.raises(KeyError, match="AI_PROVIDER_NOT_REGISTERED"):
        registry.set_default("missing")
    with pytest.raises(KeyError, match="AI_PROVIDER_NOT_REGISTERED"):
        registry.route("missing")
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED"):
        AIProviderRegistry().route()
    with pytest.raises(ValueError, match="AI_DEFAULT_PROVIDER_NOT_REGISTERED"):
        AIProviderRegistry(default_provider_id="missing")


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"kind": "unknown"}, "KNOWLEDGE_KIND_INVALID"),
        ({"text": ""}, "KNOWLEDGE_TEXT_INVALID"),
        ({"text": "x" * 2001}, "KNOWLEDGE_TEXT_INVALID"),
        ({"confidence": -0.1}, "KNOWLEDGE_CONFIDENCE_INVALID"),
        ({"confidence": 1.1}, "KNOWLEDGE_CONFIDENCE_INVALID"),
        ({"provenance": ()}, "KNOWLEDGE_PROVENANCE_INVALID"),
        ({"provenance": tuple(str(i) for i in range(21))}, "KNOWLEDGE_PROVENANCE_INVALID"),
    ],
)
def test_knowledge_items_reject_invalid_semantics(updates, error: str) -> None:
    values = {
        "kind": "fact",
        "text": "bounded",
        "confidence": 1.0,
        "provenance": ("source",),
    }
    values.update(updates)
    with pytest.raises(ValueError, match=error):
        KnowledgeItem(**values)


def test_knowledge_snapshot_deduplicates_and_bounds_provenance() -> None:
    items = tuple(
        KnowledgeItem(
            kind="fact",
            text=f"item-{index}",
            confidence=1.0,
            provenance=(f"source-{index}", "shared"),
        )
        for index in range(12)
    )
    provenance = KnowledgeSnapshot(items).provenance
    assert provenance[0:2] == ("source-0", "shared")
    assert len(provenance) == 13
    assert provenance.count("shared") == 1


def test_knowledge_engine_handles_false_player_state_and_filters_invalid_events() -> None:
    snapshot = KnowledgeEngine().build(
        {
            "player": {"level": True, "alive": False},
            "events": [None, "raw", {"event_type": None}, {"event_type": "combat"}],
            "data_quality": "complete",
        }
    )
    texts = [item.text for item in snapshot.items]
    assert "Character is level True." in texts
    assert "Character is not alive." in texts
    inference = next(item for item in snapshot.items if item.kind == "inference")
    assert inference.confidence == 0.78
    assert inference.provenance == ("event:combat",)


def test_knowledge_engine_uses_insufficient_context_when_events_have_no_provenance() -> None:
    snapshot = KnowledgeEngine().build({"events": [{}, {"event_type": ""}]})
    assert len(snapshot.items) == 1
    assert snapshot.items[0].confidence == 0.40
    assert snapshot.items[0].provenance == ("knowledge:insufficient-context",)


def test_baseline_provider_uses_high_quality_inference_and_caps_confidence() -> None:
    provider = BaselineRecommendationProvider()
    result = provider.generate(
        {
            "data_quality": "high",
            "events": [{"event_type": "combat"}],
        }
    )
    assert result.confidence == pytest.approx(0.76)
    assert result.provenance[-1] == "recommendation:progression-review"
    assert result.text.startswith("Review the most recent")
