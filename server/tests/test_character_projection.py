"""Issue #107 Phase 2 — character event projection tests."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.character_projection import (
    CHARACTER_PROJECT_TYPES,
    apply_character_projections,
    character_projection_from_event,
)
from app.main import app, store
from test_api import provision, reset_store

client = TestClient(app)


def test_character_projection_from_event_happy_and_skip():
    base = {
        "type": "character.snapshot",
        "payload": {
            "game_id": "diablo-4-pc",
            "external_id": "char-42",
            "name": "Barbarian",
            "version": 3,
            "state_json": {"level": 50, "class": "barb"},
        },
    }
    item = character_projection_from_event("u1", base)
    assert item is not None
    assert item["user_id"] == "u1"
    assert item["game_id"] == "diablo-4-pc"
    assert item["external_id"] == "char-42"
    assert item["name"] == "Barbarian"
    assert item["version"] == 3
    assert item["state_json"]["level"] == 50

    # state key alternative
    alt = {"type": "character.upsert", "payload": {"game_id": "g", "external_id": "e", "name": "N", "state": {"hp": 1}}}
    assert character_projection_from_event("u1", alt)["state_json"]["hp"] == 1

    # fold remaining keys
    fold = {"type": "character.state", "payload": {"game_id": "g", "external_id": "e", "name": "N", "extra": 9}}
    assert character_projection_from_event("u1", fold)["state_json"]["extra"] == 9

    # non-projectable type
    assert character_projection_from_event("u1", {"type": "other.event", "payload": {}}) is None
    # missing required fields
    assert character_projection_from_event("u1", {"type": "character.snapshot", "payload": {"game_id": "g"}}) is None
    assert "character.snapshot" in CHARACTER_PROJECT_TYPES


def test_apply_character_projections_upserts():
    reset_store()
    events = [
        {
            "type": "character.snapshot",
            "payload": {
                "game_id": "diablo-4-pc",
                "external_id": "ext-1",
                "name": "Hero",
                "version": 1,
                "state_json": {"level": 1},
            },
        },
        {"type": "noise.event", "payload": {}},
        {
            "type": "character.state",
            "payload": {
                "game_id": "diablo-4-pc",
                "external_id": "ext-1",
                "name": "Hero",
                "version": 2,
                "state_json": {"level": 10},
            },
        },
    ]
    applied = apply_character_projections(store, "u1", events)
    assert applied == 2
    chars = store.list_characters("u1")
    assert len(chars) == 1
    assert chars[0]["name"] == "Hero"
    assert chars[0]["version"] == 2
    assert chars[0]["state_json"]["level"] == 10


def test_event_batch_projects_character_into_read_api():
    key, device, session = provision()
    token = session["session_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "proj-batch-1"}
    payload = {
        "events": [
            {
                "event_id": "evt-proj-001",
                "device_id": device["device_id"],
                "type": "character.snapshot",
                "schema_version": 1,
                "occurred_at": "2026-09-02T10:00:00Z",
                "sequence": 0,
                "payload": {
                    "game_id": "diablo-4-pc",
                    "external_id": "wow-char-1",
                    "name": "ProjectedChar",
                    "version": 5,
                    "state_json": {"level": 60, "class": "mage"},
                },
            }
        ]
    }
    resp = client.post("/v1/events:batch", headers=headers, json=payload)
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1

    listed = client.get("/v1/characters", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    chars = listed.json()["characters"]
    assert len(chars) == 1
    assert chars[0]["name"] == "ProjectedChar"
    assert chars[0]["external_id"] == "wow-char-1"
    assert chars[0]["state_json"]["level"] == 60

    # incomplete payload still accepts event but does not create character
    headers2 = {"Authorization": f"Bearer {token}", "Idempotency-Key": "proj-batch-2"}
    incomplete = {
        "events": [
            {
                "event_id": "evt-proj-002",
                "device_id": device["device_id"],
                "type": "character.snapshot",
                "schema_version": 1,
                "occurred_at": "2026-09-02T10:01:00Z",
                "sequence": 1,
                "payload": {"hp": 100},
            }
        ]
    }
    resp2 = client.post("/v1/events:batch", headers=headers2, json=incomplete)
    assert resp2.status_code == 200
    assert resp2.json()["accepted"] == 1
    listed2 = client.get("/v1/characters", headers={"Authorization": f"Bearer {token}"})
    assert len(listed2.json()["characters"]) == 1  # still only the first
