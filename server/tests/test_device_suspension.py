import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from test_owned_device_list import device_store  # shared Memory/PostgreSQL contract


def setup(device_store, monkeypatch):
    import app.main as main
    owner = str(uuid.uuid4())
    device = device_store.register_device(owner, 'android', 'key', uuid.uuid4().hex * 2, 'challenge')
    browser = device_store.issue_session(None, owner, 300, 300)[0]
    session, refresh, _, _ = device_store.issue_session(device, owner, 300, 300)
    monkeypatch.setattr(main, 'store', device_store)
    return TestClient(main.app), owner, device, browser, session, refresh


def test_owner_suspension_denies_device_access_and_refresh_preserving_browser(device_store, monkeypatch):
    client, owner, device, browser, session, refresh = setup(device_store, monkeypatch)
    response = client.post(f'/v1/devices/{device}/suspend', headers={'Authorization': 'Bearer ' + browser})
    assert response.status_code == 200, response.text
    assert response.json() == {'suspended': True}
    assert device_store.get_device(device)['state'] == 'SUSPENDED'
    assert device_store.get_session(session) is None
    assert device_store.rotate_refresh(refresh, 300, 300) is None
    assert device_store.get_session(browser) is not None
    assert client.get('/v1/devices', headers={'Authorization': 'Bearer ' + browser}).json()['devices'][0]['state'] == 'SUSPENDED'
    assert client.post(f'/v1/devices/{device}/challenge', headers={'Authorization': 'Bearer ' + browser}).status_code == 409
    assert client.post(f'/v1/devices/{device}/suspend', headers={'Authorization': 'Bearer ' + browser}).status_code == 409
    assert client.post(f'/v1/devices/{device}/revoke', headers={'Authorization': 'Bearer ' + browser}).status_code == 200
    assert device_store.get_device(device)['state'] == 'REVOKED'


def test_foreign_account_and_missing_auth_cannot_suspend(device_store, monkeypatch):
    client, _, device, browser, _, _ = setup(device_store, monkeypatch)
    foreign = device_store.issue_session(None, str(uuid.uuid4()), 300, 300)[0]
    assert client.post(f'/v1/devices/{device}/suspend', headers={'Authorization': 'Bearer ' + foreign}).status_code == 403
    assert client.post(f'/v1/devices/{device}/suspend', headers={'Authorization': 'Bearer invalid'}).status_code == 401
    assert device_store.get_device(device)['state'] == 'ACTIVE'
    assert client.post(f'/v1/devices/{uuid.uuid4()}/suspend', headers={'Authorization': 'Bearer ' + browser}).status_code == 404


def test_revoke_wins_concurrent_suspension_without_reactivation(device_store):
    owner = str(uuid.uuid4())
    device = device_store.register_device(owner, 'android', 'key', uuid.uuid4().hex * 2, 'challenge')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda operation: operation(device), [device_store.suspend_device, device_store.revoke_device]))
    assert results[1] is True
    assert device_store.get_device(device)['state'] == 'REVOKED'
    assert device_store.suspend_device(device) is False
