"""Operator-only publication. Never imported by serving routes."""
from __future__ import annotations

from sqlalchemy import text

from app.core.knowledge_distribution import PackProfile
from app.core.knowledge_packs import load_pack


def validate_publication(raw: bytes, digest: str, review_reference: str):
    if not isinstance(review_reference, str) or not review_reference.strip() or len(review_reference) > 256:
        raise ValueError('KNOWLEDGE_REVIEW_REQUIRED')
    loaded = load_pack(raw, digest)
    if loaded.pack.status != 'validated' or loaded.pack.revoked or not loaded.pack.rules:
        raise ValueError('KNOWLEDGE_REVIEWED_RULES_REQUIRED')
    return loaded


def _require_operator(connection):
    owners = connection.execute(text('''
        SELECT count(*) FROM pg_class
        WHERE oid IN ('knowledge_packs'::regclass, 'knowledge_profile_bindings'::regclass)
          AND pg_get_userbyid(relowner)=current_user
    ''')).scalar_one()
    if owners != 2:
        raise ValueError('KNOWLEDGE_OPERATOR_CUSTODY_REQUIRED')


def publish(engine, raw: bytes, digest: str, review_reference: str, *, expected_revision: int,
            now_ms: int) -> int:
    loaded = validate_publication(raw, digest, review_reference)
    if type(expected_revision) is not int or expected_revision < 0 or type(now_ms) is not int or now_ms <= 0:
        raise ValueError('KNOWLEDGE_REVISION_INVALID')
    if loaded.pack.valid_until_ms <= now_ms:
        raise ValueError('KNOWLEDGE_PACK_EXPIRED')
    profile = PackProfile(**{key: getattr(loaded.pack, key) for key in PackProfile.model_fields})
    key = profile.key()
    with engine.begin() as connection:
        _require_operator(connection)
        # Includes first-publication races; row locking alone cannot lock a missing pointer.
        connection.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'), {'key': key})
        current = connection.execute(text('SELECT GREATEST(b.revision,p.revocation_revision) FROM knowledge_profile_bindings b JOIN knowledge_packs p ON p.digest=b.digest WHERE b.profile_key=:key FOR UPDATE OF p'), {'key': key}).scalar_one_or_none()
        if (current or 0) != expected_revision:
            raise ValueError('KNOWLEDGE_REVISION_CONFLICT')
        connection.execute(text('''INSERT INTO knowledge_packs(digest,raw,review_reference)
            VALUES (:digest,:raw,:review) ON CONFLICT(digest) DO NOTHING'''),
            {'digest': digest, 'raw': raw, 'review': review_reference})
        retained = connection.execute(text('SELECT raw, revoked_at_ms FROM knowledge_packs WHERE digest=:digest FOR UPDATE'), {'digest': digest}).mappings().one()
        if bytes(retained['raw']) != raw or retained['revoked_at_ms'] is not None:
            raise ValueError('KNOWLEDGE_CONTENT_REVOKED_OR_INVALID')
        return connection.execute(text('''
            INSERT INTO knowledge_profile_bindings(profile_key,digest,revision)
            VALUES (:key,:digest,nextval('knowledge_distribution_revision'))
            ON CONFLICT(profile_key) DO UPDATE SET digest=EXCLUDED.digest,
                revision=nextval('knowledge_distribution_revision') RETURNING revision
        '''), {'key': key, 'digest': digest}).scalar_one()


def revoke(engine, digest: str, *, now_ms: int) -> int:
    if type(now_ms) is not int or now_ms <= 0:
        raise ValueError('KNOWLEDGE_TIME_INVALID')
    with engine.begin() as connection:
        _require_operator(connection)
        row = connection.execute(text('SELECT revoked_at_ms,revocation_revision FROM knowledge_packs WHERE digest=:digest FOR UPDATE'), {'digest': digest}).mappings().first()
        if row is None:
            raise ValueError('KNOWLEDGE_PACK_UNKNOWN')
        if row['revoked_at_ms'] is not None:
            return row['revocation_revision']
        return connection.execute(text('''UPDATE knowledge_packs SET revoked_at_ms=:now,
            revocation_revision=nextval('knowledge_distribution_revision')
            WHERE digest=:digest RETURNING revocation_revision'''), {'now': now_ms, 'digest': digest}).scalar_one()
