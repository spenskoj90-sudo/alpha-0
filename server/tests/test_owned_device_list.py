import uuid

import pytest
from fastapi.testclient import TestClient
from app.core.store import MemoryStore


@pytest.fixture(params=["memory", pytest.param("postgres", marks=pytest.mark.postgres)])
def device_store(request):
    if request.param == "postgres":
        from app.main import store
        from app.core.store import PostgresStore
        assert isinstance(store, PostgresStore)
        return store
    return MemoryStore()


def test_owned_device_summary_excludes_other_accounts_and_key_material(device_store, monkeypatch):
    import app.main as main
    owner, foreign = str(uuid.uuid4()), str(uuid.uuid4())
    owned = device_store.register_device(owner, "android", "owned-key", uuid.uuid4().hex * 2, "owned-challenge")
    device_store.register_device(foreign, "android", "foreign-key", uuid.uuid4().hex * 2, "foreign-challenge")
    token = device_store.issue_session(owned, owner, 300, 300)[0]
    monkeypatch.setattr(main, "store", device_store)
    client = TestClient(main.app)
    result = client.get('/v1/devices?user_id=' + foreign, headers={'Authorization': 'Bearer ' + token})
    assert result.status_code == 200
    payload = result.json()
    assert payload['truncated'] is False
    assert [d['device_id'] for d in payload['devices']] == [owned]
    assert set(payload['devices'][0]) == {'device_id', 'platform', 'state', 'bound_at', 'last_seen_at'}
    assert 'owned-key' not in result.text and 'foreign-key' not in result.text
    assert client.get('/v1/devices', headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_device_store_keeps_revoked_records_and_hard_bounds_the_summary(device_store, monkeypatch):
    owner = str(uuid.uuid4())
    first = device_store.register_device(owner, 'android', 'first-key', uuid.uuid4().hex * 2, 'first-challenge')
    assert device_store.revoke_device(first)
    assert device_store.list_devices(owner)[0]['state'] == 'REVOKED'
    for i in range(102):
        latest = device_store.register_device(owner, 'android', f'key-{i}', uuid.uuid4().hex * 2, f'challenge-{i}')
    assert len(device_store.list_devices(owner)) == 101
    assert device_store.list_devices(str(uuid.uuid4())) == []
    import app.main as main
    monkeypatch.setattr(main, 'store', device_store)
    token = device_store.issue_session(latest, owner, 300, 300)[0]
    response = TestClient(main.app).get('/v1/devices', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 200
    assert response.json()['truncated'] is True
    assert len(response.json()['devices']) == 100
