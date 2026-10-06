"""Canonical data-only distribution. Publication is absent from serving APIs."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.core.knowledge_packs import load_pack

LEASE_MS = 60_000
MAX_SAFE_INTEGER = 9_007_199_254_740_991


class PackProfile(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    game: str = Field(min_length=1, max_length=128)
    platform: Literal['android', 'windows']
    patch: str = Field(min_length=1, max_length=64)
    environment: str = Field(min_length=1, max_length=128)
    profile: str = Field(min_length=1, max_length=128)

    def key(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True,
                                        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def manifest(row, profile: PackProfile, *, now_ms: int, known_digest: str | None = None) -> dict:
    result = {'schema_version': 1, 'status': 'unavailable', 'profile': profile.model_dump(),
              'revision': 0, 'digest': None, 'version': None, 'lease_until_ms': None,
              'server_time_ms': now_ms, 'execution_authority': False}
    if row is None or type(now_ms) is not int or not 0 < now_ms <= MAX_SAFE_INTEGER - LEASE_MS:
        return result
    if type(row['revision']) is not int or not 0 < row['revision'] <= MAX_SAFE_INTEGER:
        return result
    result['revision'] = row['revision']
    if row['revoked_at_ms'] is not None:
        result['status'] = 'revoked'
        result['digest'] = row['digest']
        return result
    try:
        pack = load_pack(bytes(row['raw']), row['digest']).pack
    except ValueError:
        return result
    if (not row['review_reference'] or pack.status != 'validated' or pack.revoked
            or pack.valid_until_ms <= now_ms
            or any(getattr(pack, key) != value for key, value in profile.model_dump().items())):
        return result
    return {**result, 'status': 'unchanged' if known_digest == row['digest'] else 'available',
            'digest': row['digest'], 'version': pack.version,
            'lease_until_ms': min(now_ms + LEASE_MS, pack.valid_until_ms)}


class KnowledgeDistribution:
    def __init__(self, engine=None):
        self.engine = engine

    def read(self, profile: PackProfile):
        if self.engine is None:
            return None
        with self.engine.connect() as connection:
            row = connection.execute(text('''
                SELECT p.raw, p.digest, p.review_reference, p.revoked_at_ms,
                       GREATEST(b.revision, p.revocation_revision) AS revision
                FROM knowledge_profile_bindings b JOIN knowledge_packs p ON p.digest=b.digest
                WHERE b.profile_key=:key
            '''), {'key': profile.key()}).mappings().first()
            return dict(row) if row else None

    def read_delta(self, profile: PackProfile, destination_digest: str, base_digest: str,
                   *, now_ms: int | None = None) -> dict | None:
        if self.engine is None:
            return None
        # A single statement snapshot observes the current pointer and both
        # revocations together; it never serves arbitrary historical destinations.
        with self.engine.connect() as connection:
            row = connection.execute(text('''
                SELECT p.raw, p.digest, p.review_reference, p.revoked_at_ms,
                       GREATEST(b.revision, p.revocation_revision) AS revision,
                       old.raw AS base_raw, old.review_reference AS base_review,
                       old.revoked_at_ms AS base_revoked
                FROM knowledge_profile_bindings b
                JOIN knowledge_packs p ON p.digest=b.digest
                JOIN knowledge_packs old ON old.digest=:base
                WHERE b.profile_key=:key AND p.digest=:destination
            '''), {'key': profile.key(), 'base': base_digest,
                   'destination': destination_digest}).mappings().first()
        if row is None or row['base_revoked'] is not None or not row['base_review']:
            return None
        # Production samples after the query/pool wait. Explicit time is only
        # a deterministic library test seam and is never accepted by the route.
        if now_ms is None:
            now_ms = time.time_ns() // 1_000_000
        if manifest(row, profile, now_ms=now_ms)['status'] != 'available':
            return None
        try:
            base = bytes(row['base_raw'])
            pack = load_pack(base, base_digest).pack
        except ValueError:
            return None
        if pack.revoked or pack.status != 'validated' or any(
                getattr(pack, key) != value for key, value in profile.model_dump().items()):
            return None
        from app.core.knowledge_delta import make_delta
        return make_delta(base, bytes(row['raw']))
