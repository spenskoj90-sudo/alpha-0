import hashlib
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.database_engine import create_service_role_engine
from app.core.knowledge_distribution import KnowledgeDistribution, PackProfile, manifest
from app.core.knowledge_publication import publish, revoke
from test_knowledge_packs import pack_data

pytestmark = pytest.mark.postgres


def material(game=None, version='1'):
    data = pack_data()
    data.update(game=game or 'fixture-' + uuid.uuid4().hex, version=version,
                valid_until_ms=int(time.time()*1000) + 600000)
    raw = json.dumps(data).encode()
    return raw, hashlib.sha256(raw).hexdigest(), PackProfile(**{k: data[k] for k in PackProfile.model_fields})


def test_postgres_publication_exact_delivery_cas_and_durable_revocation():
    engine = create_service_role_engine(os.environ['DATABASE_URL'])
    try:
        raw, digest, profile = material()
        now = int(time.time()*1000)
        revision = publish(engine, raw, digest, 'fixture:review', expected_revision=0, now_ms=now)
        repository = KnowledgeDistribution(engine)
        row = repository.read(profile)
        assert bytes(row['raw']) == raw
        assert manifest(row, profile, now_ms=now)['status'] == 'available'
        with pytest.raises(ValueError, match='REVISION_CONFLICT'):
            publish(engine, raw, digest, 'fixture:review', expected_revision=0, now_ms=now)
        raw2, digest2, _ = material(profile.game, '2')
        new_revision = publish(engine, raw2, digest2, 'fixture:review2', expected_revision=revision, now_ms=now)
        assert new_revision > revision
        assert repository.read(profile)['digest'] == digest2
        revoke_revision = revoke(engine, digest2, now_ms=now)
        assert revoke_revision > new_revision
        assert revoke(engine, digest2, now_ms=now) == revoke_revision
        engine.dispose()
        assert manifest(repository.read(profile), profile, now_ms=now)['status'] == 'revoked'
        with pytest.raises(ValueError, match='REVOKED'):
            publish(engine, raw2, digest2, 'fixture:review2', expected_revision=revoke_revision, now_ms=now)
        with engine.begin() as connection, pytest.raises(DBAPIError):
            connection.execute(text('UPDATE knowledge_packs SET raw=:raw WHERE digest=:digest'), {'raw': b'{}', 'digest': digest})
    finally:
        engine.dispose()


def test_concurrent_first_publish_has_one_winner():
    engine = create_service_role_engine(os.environ['DATABASE_URL'])
    raw, digest, profile = material()
    now = int(time.time()*1000)
    def attempt(_):
        try:
            return publish(engine, raw, digest, 'fixture:review', expected_revision=0, now_ms=now)
        except ValueError as exc:
            return str(exc)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        assert sum(type(result) is int for result in results) == 1
        assert results.count('KNOWLEDGE_REVISION_CONFLICT') == 1
    finally:
        engine.dispose()


def test_service_flag_cannot_publish_or_revoke_even_with_table_write_grant():
    owner = create_engine(os.environ['DATABASE_URL'])
    raw, digest, profile = material()
    try:
        with owner.begin() as connection:
            connection.exec_driver_sql('DROP ROLE IF EXISTS knowledge_runtime_probe')
            connection.exec_driver_sql('CREATE ROLE knowledge_runtime_probe NOLOGIN NOSUPERUSER NOBYPASSRLS')
            connection.exec_driver_sql('GRANT ALL ON knowledge_packs,knowledge_profile_bindings TO knowledge_runtime_probe')
        publish(owner, raw, digest, 'fixture:review', expected_revision=0, now_ms=int(time.time()*1000))
        with owner.begin() as connection:
            connection.exec_driver_sql('SET LOCAL ROLE knowledge_runtime_probe')
            connection.exec_driver_sql("SELECT set_config('app.service_role','true',true)")
            assert connection.execute(text('SELECT digest FROM knowledge_packs WHERE digest=:digest'), {'digest': digest}).scalar_one() == digest
            with pytest.raises(ValueError, match='OPERATOR'):
                from app.core.knowledge_publication import _require_operator
                _require_operator(connection)
            with pytest.raises(DBAPIError) as denied:
                with connection.begin_nested():
                    connection.execute(text("INSERT INTO knowledge_packs(digest,raw,review_reference) VALUES (:digest,:raw,'fixture')"), {'digest': 'f'*64, 'raw': raw})
            assert denied.value.orig.sqlstate == '42501'
            # PostgreSQL TRUNCATE bypasses RLS and row-level DELETE triggers.
            # An accidental ALL grant must not erase content or tombstones.
            for sql in ['TRUNCATE knowledge_profile_bindings',
                        'TRUNCATE knowledge_packs CASCADE',
                        'TRUNCATE knowledge_profile_bindings,knowledge_packs']:
                with pytest.raises(DBAPIError) as denied:
                    with connection.begin_nested():
                        connection.exec_driver_sql(sql)
                assert denied.value.orig.sqlstate == '23514'
            assert connection.execute(text('SELECT digest FROM knowledge_packs WHERE digest=:digest'), {'digest': digest}).scalar_one() == digest
            for sql in ['UPDATE knowledge_packs SET revoked_at_ms=1,revocation_revision=1 WHERE digest=:digest',
                        'DELETE FROM knowledge_packs WHERE digest=:digest',
                        'UPDATE knowledge_profile_bindings SET revision=123 WHERE profile_key=:key']:
                result = connection.execute(text(sql), {'digest': digest, 'key': profile.key()})
                assert result.rowcount == 0
            connection.exec_driver_sql("SELECT set_config('app.service_role','false',true)")
            assert connection.execute(text('SELECT digest FROM knowledge_packs WHERE digest=:digest'), {'digest': digest}).first() is None
    finally:
        with owner.begin() as connection:
            connection.exec_driver_sql('DROP OWNED BY knowledge_runtime_probe')
            connection.exec_driver_sql('DROP ROLE knowledge_runtime_probe')
        owner.dispose()


def test_delta_snapshot_binds_current_destination_and_nonrevoked_exact_profile_base():
    from app.core.knowledge_delta import reconstruct_delta
    engine = create_service_role_engine(os.environ['DATABASE_URL'])
    try:
        raw, digest, profile = material()
        now = int(time.time()*1000)
        revision = publish(engine, raw, digest, 'fixture:delta-review', expected_revision=0, now_ms=now)
        raw2, digest2, _ = material(profile.game, '2')
        publish(engine, raw2, digest2, 'fixture:delta-review2', expected_revision=revision, now_ms=now)
        repository = KnowledgeDistribution(engine)
        delta = repository.read_delta(profile, digest2, digest, now_ms=now)
        assert reconstruct_delta(raw, delta, expected_digest=digest2) == raw2
        assert repository.read_delta(profile, digest, digest2, now_ms=now) is None
        other, other_digest, _ = material()
        publish(engine, other, other_digest, 'fixture:other-profile', expected_revision=0, now_ms=now)
        assert repository.read_delta(profile, digest2, other_digest, now_ms=now) is None
        revoke(engine, digest, now_ms=now)
        assert repository.read_delta(profile, digest2, digest, now_ms=now) is None
        assert manifest(repository.read(profile), profile, now_ms=now)['status'] == 'available'
        revoke(engine, digest2, now_ms=now)
        assert repository.read_delta(profile, digest2, digest2, now_ms=now) is None
    finally:
        engine.dispose()
