import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import sleep

import pytest
from sqlalchemy import event, text

from fastapi.testclient import TestClient

from test_owned_device_list import device_store  # shared Memory/PostgreSQL contract


def setup(device_store, monkeypatch):
    import app.main as main
    owner = str(uuid.uuid4())
    device = device_store.register_device(owner, 'android', 'key', uuid.uuid4().hex * 2, uuid.uuid4().hex)
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
    foreign_user = str(uuid.uuid4())
    if hasattr(device_store, "engine"):
        with device_store.engine.begin() as conn:
            conn.execute(text("INSERT INTO identities(user_handle) VALUES (:user)"), {"user": foreign_user})
    foreign = device_store.issue_session(None, foreign_user, 300, 300)[0]
    assert client.post(f'/v1/devices/{device}/suspend', headers={'Authorization': 'Bearer ' + foreign}).status_code == 403
    assert client.post(f'/v1/devices/{device}/suspend', headers={'Authorization': 'Bearer invalid'}).status_code == 401
    assert device_store.get_device(device)['state'] == 'ACTIVE'
    assert client.post(f'/v1/devices/{uuid.uuid4()}/suspend', headers={'Authorization': 'Bearer ' + browser}).status_code == 404


def test_revoke_wins_concurrent_suspension_without_reactivation(device_store):
    owner = str(uuid.uuid4())
    device = device_store.register_device(owner, 'android', 'key', uuid.uuid4().hex * 2, uuid.uuid4().hex)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda operation: operation(device), [device_store.suspend_device, device_store.revoke_device]))
    assert results[1] is True
    assert device_store.get_device(device)['state'] == 'REVOKED'
    assert device_store.suspend_device(device) is False


def test_suspension_audit_attributes_browser_principal_not_target(monkeypatch):
    from app.core.store import MemoryStore
    device_store = MemoryStore()
    client, owner, device, browser, _, _ = setup(device_store, monkeypatch)
    assert client.post(f'/v1/devices/{device}/suspend', headers={'Authorization': 'Bearer ' + browser}).status_code == 200
    audit = [item for item in device_store.audit if item['action'] == 'device:suspend'][-1]
    assert audit['actor_user_id'] == owner
    assert audit['actor_device_id'] is None
    assert audit['metadata']['target_device_id'] == device


@pytest.mark.postgres
def test_suspension_serializes_with_inflight_refresh_insert():
    from app.main import store
    from app.core.store import PostgresStore
    assert isinstance(store, PostgresStore)
    owner = str(uuid.uuid4())
    device = store.register_device(owner, 'android', 'key', uuid.uuid4().hex * 2, uuid.uuid4().hex)
    _, refresh, _, _ = store.issue_session(device, owner, 300, 300)
    selected, release = Event(), Event()

    def after_select(conn, cursor, statement, parameters, context, executemany):
        if 'FROM sessions s JOIN identities i' in statement and 'FOR UPDATE OF s' in statement:
            selected.set()
            assert release.wait(15), 'held refresh must resume'

    event.listen(store.engine, 'after_cursor_execute', after_select)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rotating = pool.submit(store.rotate_refresh, refresh, 300, 300)
            assert selected.wait(15), 'refresh reached its locked session row'
            suspending = pool.submit(store.suspend_device, device)
            # Suspension and rotation contend for the same device row. Without
            # consistent lock order, bulk revoke may miss the inserted session.
            sleep(0.2)
            release.set()
            assert suspending.result(timeout=15) is True
            rotating.result(timeout=15)
    finally:
        release.set()
        event.remove(store.engine, 'after_cursor_execute', after_select)

    with store.engine.begin() as conn:
        live = conn.execute(
            text("SELECT count(*) FROM sessions WHERE device_id=:id AND revoked_at IS NULL"),
            {'id': device},
        ).scalar_one()
    assert live == 0
