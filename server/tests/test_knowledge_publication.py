import hashlib
import json

import pytest
from app.core import knowledge_publication as publication
from test_knowledge_packs import pack_data


def test_publication_requires_independent_review_and_full_digest():
    raw = json.dumps(pack_data()).encode()
    digest = hashlib.sha256(raw).hexdigest()
    assert publication.validate_publication(raw, digest, 'review:fixture').digest == digest
    for review in ['', ' '*4, 'x'*257]:
        with pytest.raises(ValueError): publication.validate_publication(raw, digest, review)
    with pytest.raises(ValueError): publication.validate_publication(raw, 'a'*64, 'review:fixture')


def test_draft_and_embedded_revocation_cannot_be_published_as_active():
    for changes in [{'status': 'draft'}, {'revoked': True}, {'rules': []}]:
        raw = json.dumps({**pack_data(), **changes}).encode()
        with pytest.raises(ValueError):
            publication.validate_publication(raw, hashlib.sha256(raw).hexdigest(), 'review:fixture')


@pytest.mark.parametrize('revision,now', [(True, 1500), (-1, 1500), (0, True), (0, 0), (0, None)])
def test_invalid_publication_clock_or_revision_never_reaches_database(revision, now):
    raw = json.dumps(pack_data()).encode()
    with pytest.raises(ValueError, match='REVISION_INVALID'):
        publication.publish(None, raw, hashlib.sha256(raw).hexdigest(), 'review:fixture',
                            expected_revision=revision, now_ms=now)


def test_expired_content_cannot_reach_publication_database():
    raw = json.dumps(pack_data()).encode()
    with pytest.raises(ValueError, match='EXPIRED'):
        publication.publish(None, raw, hashlib.sha256(raw).hexdigest(), 'review:fixture',
                            expected_revision=0, now_ms=100000)
    with pytest.raises(ValueError, match='TIME_INVALID'):
        publication.revoke(None, hashlib.sha256(raw).hexdigest(), now_ms=True)
