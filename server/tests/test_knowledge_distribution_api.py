import hashlib
import json

from test_api import client, provision
from test_knowledge_distribution import profile, row


def params():
    return profile().model_dump()


def test_distribution_requires_real_session_and_rejects_unbound_raw(monkeypatch):
    from app.main import knowledge_distribution
    monkeypatch.setattr(knowledge_distribution, 'read', lambda _profile: row())
    _, _, session = provision()
    headers = {'Authorization': 'Bearer ' + session['session_token']}
    assert client.get('/v1/knowledge/manifest', params=params(), headers={'Authorization': 'Bearer invalid'}).status_code == 401
    manifest = client.get('/v1/knowledge/manifest', params=params(), headers=headers)
    assert manifest.status_code == 200
    assert manifest.json()['execution_authority'] is False
    assert manifest.headers['cache-control'] == 'no-store'
    digest = row()['digest']
    raw = client.get('/v1/knowledge/packs/' + digest, params=params(), headers=headers)
    # Fixture clock is expired under real endpoint time: cannot be delivered.
    assert raw.status_code == 404
    assert client.get('/v1/knowledge/packs/' + 'a'*64, params=params(), headers=headers).status_code == 404
    assert client.get('/v1/knowledge/manifest', params={**params(), 'platform': 'unknown'}, headers=headers).status_code == 422


def test_authenticated_exact_profile_delivery_and_revocation(monkeypatch):
    from app.main import knowledge_distribution
    from test_knowledge_packs import pack_data
    data = pack_data(); data['valid_until_ms'] = 4102444800000
    raw = json.dumps(data).encode(); digest = hashlib.sha256(raw).hexdigest()
    record = row(raw=raw, digest=digest)
    monkeypatch.setattr(knowledge_distribution, 'read', lambda _profile: record)
    _, _, session = provision()
    headers = {'Authorization': 'Bearer ' + session['session_token']}
    route = '/v1/knowledge/packs/' + digest
    assert client.get(route, params=params(), headers=headers).content == raw
    assert client.get(route, params={**params(), 'patch': 'different'}, headers=headers).status_code == 404
    value = client.get('/v1/knowledge/manifest', params={**params(), 'known_digest': digest}, headers=headers).json()
    assert value['status'] == 'unchanged'
    record['revoked_at_ms'] = 1
    assert client.get(route, params=params(), headers=headers).status_code == 404
    assert client.get('/v1/knowledge/manifest', params=params(), headers=headers).json()['status'] == 'revoked'
    assert client.post(route, headers=headers, content=raw).status_code == 405


def test_database_failure_is_safe_503_with_no_credential_detail(monkeypatch):
    from app.main import knowledge_distribution
    def broken(_):
        from sqlalchemy.exc import OperationalError
        raise OperationalError('secret database URL', {}, Exception('credential secret'))
    monkeypatch.setattr(knowledge_distribution, 'read', broken)
    _, _, session = provision()
    response = client.get('/v1/knowledge/manifest', params=params(), headers={'Authorization': 'Bearer ' + session['session_token']})
    assert response.status_code == 503
    assert 'secret' not in response.text


def test_delta_route_requires_session_and_exact_current_destination(monkeypatch):
    from app.main import knowledge_distribution
    from app.core.knowledge_delta import make_delta, reconstruct_delta
    from test_knowledge_packs import pack_data
    base = row()['raw']; data = pack_data(); data['version'] = '2'
    destination = json.dumps(data).encode(); digest = hashlib.sha256(destination).hexdigest()
    delta = make_delta(base, destination)
    monkeypatch.setattr(knowledge_distribution, 'read_delta',
                        lambda p, d, b, now_ms=None: delta if p == profile() and d == digest and b == row()['digest'] else None,
                        raising=False)
    _, _, session = provision()
    headers = {'Authorization': 'Bearer ' + session['session_token']}
    query = {**params(), 'base_digest': row()['digest']}
    url = '/v1/knowledge/deltas/' + digest
    assert client.get(url, params=query, headers={'Authorization': 'Bearer invalid'}).status_code == 401
    response = client.get(url, params=query, headers=headers)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert reconstruct_delta(base, response.json(), expected_digest=digest) == destination
    assert client.get(url, params={**query, 'patch': '2'}, headers=headers).status_code == 404
    assert client.get(url, params={**query, 'base_digest': '../unbound'}, headers=headers).status_code == 422
    assert client.post(url, params=query, headers=headers).status_code == 405


def test_delta_expiry_is_checked_after_database_snapshot_returns(monkeypatch):
    from app.main import knowledge_distribution
    from app.core import knowledge_distribution_routes
    from test_knowledge_packs import pack_data
    _, _, session = provision()
    headers = {'Authorization': 'Bearer ' + session['session_token']}
    now = [1000]
    monkeypatch.setattr(knowledge_distribution_routes.time, 'time_ns', lambda: now[0] * 1_000_000)
    data = pack_data(); data['valid_until_ms'] = 1500
    destination = json.dumps(data).encode(); digest = hashlib.sha256(destination).hexdigest()
    record = row(raw=destination, digest=digest)
    record.update(base_raw=row()['raw'], base_review='fixture:review', base_revoked=None)

    class SnapshotConnection:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, statement, bindings):
            assert bindings == {'key': profile().key(), 'base': row()['digest'], 'destination': digest}
            now[0] = 2000  # An external DB wait crosses the pack's validity boundary.
            return self
        def mappings(self): return self
        def first(self): return record

    class SnapshotEngine:
        def connect(self): return SnapshotConnection()

    monkeypatch.setattr(knowledge_distribution, 'engine', SnapshotEngine())
    response = client.get('/v1/knowledge/deltas/' + digest,
                          params={**params(), 'base_digest': row()['digest']}, headers=headers)
    assert response.status_code == 404
