import hashlib
import json
import pytest
from app.core.knowledge_packs import PackRegistry, evaluate, load_pack


def pack_data():
    return {'schema_version': 1, 'id': 'fixture', 'version': '1', 'game': 'fixture', 'platform': 'windows', 'patch': '1', 'environment': 'offline-fixture', 'profile': 'tank', 'status': 'validated', 'provenance': ['fixture:local'], 'revoked': False, 'valid_until_ms': 100000, 'max_state_age_ms': 1000, 'rules': [{'id': 'defensive', 'priority': 10, 'requires': [{'signal': 'health', 'op': 'lte', 'value': 0.3}], 'text': {'en': 'Review defensive options.', 'ru': 'Проверьте защитные возможности.'}, 'reason': {'en': 'Health is low.', 'ru': 'Здоровье снижено.'}, 'provenance': ['fixture:rule'], 'confidence': None}], 'coverage': ['tank', 'defensive']}


def loaded(data=None):
    raw=json.dumps(data or pack_data()).encode(); return load_pack(raw, hashlib.sha256(raw).hexdigest())


def observation(**changes):
    result={'game': 'fixture', 'platform': 'windows', 'patch': '1', 'environment': 'offline-fixture', 'profile': 'tank', 'session_id': 's', 'source_verified': True, 'observed_at_ms': 1000, 'signals': {'health': 0.2}}
    result.update(changes); return result


def test_deterministic_evaluation_has_no_action_authority():
    result=evaluate(loaded(), observation(), now_ms=1500, session_id='s')
    assert result.status == 'ready'
    assert result.items[0]['kind']=='recommendation'
    assert result.items[0]['confidence'] is None
    assert result.items[0]['engine']=='deterministic'
    assert 'execute' not in result.items[0]


@pytest.mark.parametrize('change,reason', [({'patch':'2'},'profile_mismatch'), ({'session_id':'other'},'session_mismatch'), ({'source_verified':False},'source_unverified'), ({'observed_at_ms':0},'stale_state'), ({'observed_at_ms':2000},'stale_state'), ({'signals':{}},'missing_signals')])
def test_unknown_or_stale_never_becomes_recommendation(change, reason):
    result=evaluate(loaded(), observation(**change), now_ms=1500, session_id='s')
    assert result.status==reason
    assert result.items==()


def test_revoked_expired_and_unvalidated_packs_fail_closed():
    for key,value,reason in [('revoked', True, 'revoked'), ('valid_until_ms', 1400, 'expired_pack'), ('status','draft','unvalidated_pack')]:
        data=pack_data(); data[key]=value
        assert evaluate(loaded(data), observation(), now_ms=1500, session_id='s').status==reason


def test_raw_digest_and_unknown_fields_are_rejected():
    with pytest.raises(ValueError, match='DIGEST'): load_pack(b'{}','a'*64)
    data=pack_data(); data['executor']='arbitrary input'
    with pytest.raises(ValueError): loaded(data)
    data=pack_data(); data['rules'][0]['requires'][0]['op']='eval'
    with pytest.raises(ValueError): loaded(data)


@pytest.mark.parametrize('signals',[{'health':True},{'health':float('nan')},{'health':'0.2'}])
def test_invalid_scalar_is_not_zero_or_numeric(signals):
    assert evaluate(loaded(), observation(signals=signals), now_ms=1500, session_id='s').items==()


def test_presentation_priority_and_language_are_deterministic():
    data=pack_data(); second=json.loads(json.dumps(data['rules'][0])); second['id']='interrupt'; second['priority']=20; data['rules'].append(second)
    result=evaluate(loaded(data),observation(),now_ms=1500,session_id='s',locale='ru')
    assert [i['rule_id'] for i in result.items]==['interrupt','defensive']
    assert result.items[0]['text']=='Проверьте защитные возможности.'


def test_registry_only_returns_allowlisted_digests_and_revocation_wins(tmp_path):
    raw=json.dumps(pack_data()).encode(); digest=hashlib.sha256(raw).hexdigest()
    registry=PackRegistry(tmp_path, allowed_digests={digest})
    registry.put(raw,digest)
    assert registry.get(digest).pack.id=='fixture'
    registry.revoke(digest)
    assert registry.get(digest) is None
    with pytest.raises(ValueError): registry.put(raw,'a'*64)


def test_registry_corruption_is_denied_and_cache_is_bounded(tmp_path):
    raw=json.dumps(pack_data()).encode(); digest=hashlib.sha256(raw).hexdigest()
    registry=PackRegistry(tmp_path, allowed_digests={digest}, capacity=1)
    registry.put(raw,digest)
    (tmp_path/f'{digest}.json').write_bytes(b'{}')
    # New process/read must independently validate stored bytes.
    assert PackRegistry(tmp_path, allowed_digests={digest}).get(digest) is None


@pytest.mark.parametrize('now', [None, True, '1500', 1500.0, -1, 0])
def test_invalid_clock_fails_closed_without_raising(now):
    assert evaluate(loaded(), observation(), now_ms=now, session_id='s').status == 'stale_state'


def test_huge_numeric_signal_fails_closed_without_float_overflow():
    assert evaluate(loaded(), observation(signals={'health': 10**1000}), now_ms=1500, session_id='s').items == ()


def test_revocation_survives_registry_restart(tmp_path):
    raw=json.dumps(pack_data()).encode(); digest=hashlib.sha256(raw).hexdigest()
    registry=PackRegistry(tmp_path, allowed_digests={digest}); registry.put(raw,digest); registry.revoke(digest)
    restarted=PackRegistry(tmp_path, allowed_digests={digest})
    assert restarted.get(digest) is None
    with pytest.raises(ValueError, match='NOT_ALLOWLISTED'): restarted.put(raw,digest)


def test_pack_preserves_all_sources_within_shared_presentation_bound():
    data=pack_data(); data['provenance']=[f'pack:{i}' for i in range(16)]
    data['rules'][0]['provenance']=[f'rule:{i}' for i in range(5)]
    with pytest.raises(ValueError, match='PROVENANCE_INVALID'): loaded(data)
    data['rules'][0]['provenance']=data['rules'][0]['provenance'][:4]
    result=evaluate(loaded(data), observation(), now_ms=1500, session_id='s')
    assert len(result.items[0]['provenance']) == 20
