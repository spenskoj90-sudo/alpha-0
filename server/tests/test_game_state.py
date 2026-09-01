"""Phase 1 characters/game-state domain tests (issue #107)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app, store
from tests.test_api import provision, reset_store

client = TestClient(app)


def test_list_and_get_characters_with_idor():
    _, _, session = provision()
    token = session["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    empty = client.get("/v1/characters", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["characters"] == []

    created = store.upsert_character(
        {
            "user_id": "u1",
            "game_id": "diablo-4-pc",
            "external_id": "char-1",
            "name": "TestChar",
            "version": 1,
            "state_json": {"level": 10},
        }
    )
    listed = client.get("/v1/characters", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["characters"]) == 1
    assert listed.json()["characters"][0]["name"] == "TestChar"

    detail = client.get(f"/v1/characters/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]
    assert detail.json()["state_json"]["level"] == 10

    other_access, _, _, _ = store.issue_session(None, "u2", 3600, 86400)
    foreign = client.get(f"/v1/characters/{created['id']}", headers={"Authorization": f"Bearer {other_access}"})
    assert foreign.status_code == 403
    assert foreign.json()["code"] == "CHARACTER_SCOPE_MISMATCH"

    missing = client.get("/v1/characters/00000000-0000-0000-0000-000000000099", headers=headers)
    assert missing.status_code == 404


def test_games_catalog_and_access():
    _, _, session = provision()
    token = session["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    games = client.get("/v1/games", headers=headers)
    assert games.status_code == 200
    ids = {g["id"] for g in games.json()["games"]}
    assert "diablo-4-pc" in ids

    detail = client.get("/v1/games/diablo-4-pc", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Diablo IV"

    missing = client.get("/v1/games/no-such-game", headers=headers)
    assert missing.status_code == 404

    access_denied = client.get("/v1/games/diablo-4-pc/access", headers=headers)
    assert access_denied.status_code == 200
    assert access_denied.json()["allowed"] is False

    now = datetime.now(UTC)
    store.create_entitlement(
        {
            "id": "ent-test-1",
            "user_id": "u1",
            "game_id": "diablo-4-pc",
            "source": "test",
            "status": "ACTIVE",
            "valid_from": now - timedelta(days=1),
            "valid_until": now + timedelta(days=30),
        }
    )
    access_ok = client.get("/v1/games/diablo-4-pc/access", headers=headers)
    assert access_ok.status_code == 200
    body = access_ok.json()
    assert body["allowed"] is True
    assert len(body["entitlements"]) >= 1


def test_unauthenticated_game_state_rejected():
    reset_store()
    for path in ("/v1/characters", "/v1/games", "/v1/games/diablo-4-pc", "/v1/games/diablo-4-pc/access"):
        response = client.get(path)
        assert response.status_code in (401, 422)
