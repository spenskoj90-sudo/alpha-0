from datetime import UTC, datetime

from app.core.knowledge_engine import KnowledgeEngine, knowledge_context


NOW = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)


def test_knowledge_engine_derives_fact_and_inference_with_provenance() -> None:
    snapshot = KnowledgeEngine().build(
        {
            "data_quality": "high",
            "player": {"level": 27, "alive": True},
            "events": [
                {"event_type": "mission_completed", "sequence": 1},
                {"event_type": "inventory_changed", "sequence": 2},
            ],
        }
    )

    assert snapshot.items[0].kind == "fact"
    assert snapshot.items[0].confidence == 1.0
    assert "character:level:27" in snapshot.provenance
    assert any(item.kind == "inference" for item in snapshot.items)
    assert "event:mission_completed" in snapshot.provenance


def test_knowledge_engine_degrades_confidence_for_weak_context() -> None:
    snapshot = KnowledgeEngine().build(
        {"data_quality": "low", "events": [{"event_type": "combat", "sequence": 1}]}
    )

    inference = next(item for item in snapshot.items if item.kind == "inference")
    assert inference.confidence == 0.64


def test_knowledge_context_is_bounded_and_does_not_copy_raw_payload() -> None:
    context = {
        "data_quality": "high",
        "player": {"level": 10, "alive": True},
        "events": [{"event_type": "combat", "sequence": 1}],
        "payload": {"secret": "must-not-cross-boundary"},
    }

    projected = knowledge_context(context)

    assert "payload" not in projected
    assert projected["items"]
    assert all(set(item) == {"kind", "text", "confidence", "provenance"} for item in projected["items"])
