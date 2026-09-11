import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.postgres


def test_postgres_game_event_outbox_and_character_version_guard() -> None:
    from app.main import app, store
    from app.core.store import PostgresStore
    from test_api import provision

    if not isinstance(store, PostgresStore):
        pytest.skip("PostgresStore is required")

    client = TestClient(app)
    _, _, session = provision()
    token = session["session_token"]
    device_id = session["device_id"]

    response = client.post(
        "/v1/events:batch",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "ugs-consistency-batch"},
        json={
            "events": [
                {
                    "event_id": "ugs-consistency-event-1",
                    "device_id": device_id,
                    "type": "character.snapshot",
                    "schema_version": 1,
                    "occurred_at": "2026-09-01T12:00:00Z",
                    "sequence": 0,
                    "payload": {"game_id": "diablo-4-pc", "external_id": "consistency-1", "name": "Consistency"},
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted"] == 1

    store.upsert_character(
        {
            "user_id": "u1",
            "game_id": "diablo-4-pc",
            "external_id": "consistency-1",
            "name": "Consistency",
            "version": 5,
            "state_json": {"level": 50},
        }
    )
    store.upsert_character(
        {
            "user_id": "u1",
            "game_id": "diablo-4-pc",
            "external_id": "consistency-1",
            "name": "STALE",
            "version": 4,
            "state_json": {"level": 40},
        }
    )

    with store.engine.connect() as conn:
        outbox = conn.execute(
            text("SELECT COUNT(*) FROM outbox_events WHERE aggregate_type='game_event' AND aggregate_id=(SELECT id FROM game_events WHERE event_id=:eid)"),
            {"eid": "ugs-consistency-event-1"},
        ).scalar_one()
        character = conn.execute(
            text("SELECT version, name, state_json->>'level' FROM characters c JOIN identities i ON i.id=c.identity_id WHERE i.user_handle=:u AND c.external_id=:e"),
            {"u": "u1", "e": "consistency-1"},
        ).one()

    assert outbox == 1
    assert character[0] == 5
    assert character[1] == "Consistency"
    assert character[2] == "50"
