import hashlib
import json

import pytest
from app.core import knowledge_distribution as distribution
from test_knowledge_packs import pack_data


def row(**changes):
    data = pack_data()
    raw = json.dumps(data).encode()
    result = dict(raw=raw, digest=hashlib.sha256(raw).hexdigest(), revision=1,
                  review_reference='fixture:independent-review', revoked_at_ms=None)
    result.update(changes)
    return result


def profile():
    return distribution.PackProfile(game='fixture', platform='windows', patch='1',
                                    environment='offline-fixture', profile='tank')


def test_manifest_pins_bytes_profile_revision_and_bounded_offline_lease():
    value = distribution.manifest(row(), profile(), now_ms=1500)
    assert value['status'] == 'available'
    assert value['digest'] == row()['digest']
    assert value['lease_until_ms'] == 61500
    assert value['profile'] == profile().model_dump()
    assert value['execution_authority'] is False
    assert value['revision'] == 1
    assert distribution.manifest(row(), profile(), now_ms=99900)['lease_until_ms'] == 100000


@pytest.mark.parametrize('changed,expected', [({'revoked_at_ms': 1200}, 'revoked'),
                                             ({'review_reference': ''}, 'unavailable'),
                                             ({'digest': 'a'*64}, 'unavailable'),
                                             ({'raw': b'{}'}, 'unavailable')])
def test_no_promotion_or_bytes_for_invalid_content(changed, expected):
    assert distribution.manifest(row(**changed), profile(), now_ms=1500)['status'] == expected


def test_expired_draft_and_cross_profile_are_unavailable():
    for field, value in [('valid_until_ms', 1400), ('status', 'draft'), ('patch', '2')]:
        data = pack_data(); data[field] = value
        raw = json.dumps(data).encode()
        assert distribution.manifest(row(raw=raw, digest=hashlib.sha256(raw).hexdigest()),
                                     profile(), now_ms=1500)['status'] == 'unavailable'
    assert distribution.manifest(None, profile(), now_ms=1500)['status'] == 'unavailable'


def test_exact_digest_hint_still_rechecks_revocation_and_expiry():
    digest = row()['digest']
    assert distribution.manifest(row(), profile(), now_ms=1500, known_digest=digest)['status'] == 'unchanged'
    assert distribution.manifest(row(revoked_at_ms=1499), profile(), now_ms=1500, known_digest=digest)['status'] == 'revoked'
    assert distribution.manifest(row(), profile(), now_ms=100000, known_digest=digest)['status'] == 'unavailable'


def test_profile_key_is_unambiguous_and_input_bounded():
    assert profile().key() != distribution.PackProfile(**{**profile().model_dump(), 'patch': '2'}).key()
    with pytest.raises(ValueError): distribution.PackProfile(**{**profile().model_dump(), 'patch': ''})
    with pytest.raises(ValueError): distribution.PackProfile(**{**profile().model_dump(), 'extra': 'x'})


def test_delta_reconstructs_complete_destination_bytes_and_validates_trusted_digest():
    from app.core.knowledge_delta import make_delta, reconstruct_delta
    base = row()['raw']
    data = pack_data(); data['version'] = '2'; data['rules'][0]['text']['ru'] = 'Новый совет.'
    destination = json.dumps(data, ensure_ascii=False).encode()
    digest = hashlib.sha256(destination).hexdigest()
    delta = make_delta(base, destination)
    assert reconstruct_delta(base, delta, expected_digest=digest) == destination
    with pytest.raises(ValueError, match='DIGEST'):
        reconstruct_delta(base, delta, expected_digest='a'*64)
    with pytest.raises(ValueError, match='BASE'):
        reconstruct_delta(b'{}', delta, expected_digest=digest)


def test_delta_rejects_corruption_oversize_unsafe_types_and_executable_fields():
    from app.core.knowledge_delta import make_delta, reconstruct_delta
    base = row()['raw']; data = pack_data(); data['version'] = '2'
    destination = json.dumps(data).encode(); digest = hashlib.sha256(destination).hexdigest()
    delta = make_delta(base, destination)
    for changes in [{'insert_b64': '!!!'}, {'prefix_bytes': True}, {'prefix_bytes': 262145},
                    {'suffix_bytes': len(base)}, {'destination_size': 0}, {'execute': 'input'},
                    {'insert_b64': 'x'*349529}, {'destination_digest': 'b'*64}]:
        with pytest.raises(ValueError):
            reconstruct_delta(base, {**delta, **changes}, expected_digest=digest)
    with pytest.raises(ValueError):
        make_delta(b'x'*262145, destination)


def test_delta_cannot_install_digest_valid_non_pack_content():
    from app.core.knowledge_delta import make_delta, reconstruct_delta
    base = row()['raw']; destination = b'{"execute":"arbitrary"}'
    with pytest.raises(ValueError):
        reconstruct_delta(base, make_delta(base, destination),
                          expected_digest=hashlib.sha256(destination).hexdigest())


@pytest.mark.parametrize('now', [True, 0, -1, 1500.5, None, 9007199254740992])
def test_distribution_invalid_clock_cannot_lease_content(now):
    value = distribution.manifest(row(), profile(), now_ms=now)
    assert value['status'] == 'unavailable'
    assert value['lease_until_ms'] is None


def test_delta_schema_boolean_is_not_a_supported_version():
    from app.core.knowledge_delta import make_delta, reconstruct_delta
    raw = row()['raw']; digest = row()['digest']
    delta = make_delta(raw, raw)
    with pytest.raises(ValueError):
        reconstruct_delta(raw, {**delta, 'schema_version': True}, expected_digest=digest)


def test_zero_suffix_delta_and_missing_canonical_store_are_safe():
    from app.core.knowledge_delta import make_delta, reconstruct_delta
    raw = row()['raw']; destination = raw + b'\n'
    digest = hashlib.sha256(destination).hexdigest()
    delta = make_delta(raw, destination)
    assert delta['suffix_bytes'] == 0
    assert reconstruct_delta(raw, delta, expected_digest=digest) == destination
    store = distribution.KnowledgeDistribution()
    assert store.read(profile()) is None
    assert store.read_delta(profile(), digest, row()['digest'], now_ms=1500) is None
