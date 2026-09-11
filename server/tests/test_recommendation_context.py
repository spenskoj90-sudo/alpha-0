from datetime import UTC, datetime

from app.core.recommendation_context import recommendation_context
from app.core.unified_game_state import SourceIdentity, UGSState


def test_recommendation_context_is_bounded_and_excludes_raw_payloads() -> None:
    now = datetime.now(UTC)
    state = UGSState(
        schema_version="1.0",
        state_id="state-1",
        session_id="session-1",
        sequence=3,
        observed_at=now,
        ingested_at=now,
        source=SourceIdentity(adapter_id="wow-conservative", profile="wotlk-3.3.5a"),
        provenance=["adapter:test"],
    )
    context = recommendation_context(state)
    assert context["session_id"] == "session-1"
    assert context["source"]["adapter_id"] == "wow-conservative"
    assert "payload" not in context
