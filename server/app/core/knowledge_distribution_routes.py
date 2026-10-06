"""Authenticated read-only distribution; no remote publication or evaluation."""

import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from app.core.knowledge_distribution import KnowledgeDistribution, PackProfile, manifest


def install_knowledge_distribution_routes(app, *, distribution: KnowledgeDistribution,
                                          principal_from_token, require_bearer,
                                          authorize_request, request_id):
    def profile_query(game: Annotated[str, Query(min_length=1, max_length=128)],
                      platform: Annotated[str, Query(pattern='^(android|windows)$')],
                      patch: Annotated[str, Query(min_length=1, max_length=64)],
                      environment: Annotated[str, Query(min_length=1, max_length=128)],
                      profile: Annotated[str, Query(min_length=1, max_length=128)]) -> PackProfile:
        return PackProfile(game=game, platform=platform, patch=patch,
                           environment=environment, profile=profile)

    def read(request, authorization, rid, profile, operation=None):
        principal = principal_from_token(require_bearer(authorization))
        authorize_request(principal, 'game:read', 'game:*', request_id(request, rid))
        try:
            return operation() if operation is not None else distribution.read(profile)
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail='KNOWLEDGE_UNAVAILABLE') from None

    @app.get('/v1/knowledge/manifest')
    def get_manifest(request: Request, response: Response,
                     profile: Annotated[PackProfile, Depends(profile_query)],
                     authorization: str = Header(..., alias='Authorization'),
                     rid: str | None = Header(None, alias='X-Request-ID'),
                     known_digest: Annotated[str | None, Query(pattern='^[0-9a-f]{64}$')] = None):
        row = read(request, authorization, rid, profile)
        response.headers['Cache-Control'] = 'no-store'
        return manifest(row, profile, now_ms=time.time_ns() // 1_000_000, known_digest=known_digest)

    @app.get('/v1/knowledge/packs/{digest}')
    def get_pack(digest: str, request: Request,
                 profile: Annotated[PackProfile, Depends(profile_query)],
                 authorization: str = Header(..., alias='Authorization'),
                 rid: str | None = Header(None, alias='X-Request-ID')):
        row = read(request, authorization, rid, profile)
        value = manifest(row, profile, now_ms=time.time_ns() // 1_000_000)
        if value['status'] != 'available' or value['digest'] != digest:
            raise HTTPException(status_code=404, detail='KNOWLEDGE_PACK_UNAVAILABLE')
        return Response(content=bytes(row['raw']), media_type='application/json',
                        headers={'Cache-Control': 'no-store', 'ETag': '"' + digest + '"'})

    @app.get('/v1/knowledge/deltas/{digest}')
    def get_delta(digest: str, request: Request, response: Response,
                  profile: Annotated[PackProfile, Depends(profile_query)],
                  base_digest: Annotated[str, Query(pattern='^[0-9a-f]{64}$')],
                  authorization: str = Header(..., alias='Authorization'),
                  rid: str | None = Header(None, alias='X-Request-ID')):
        delta = read(request, authorization, rid, profile,
                     operation=lambda: distribution.read_delta(
                         profile, digest, base_digest))
        if delta is None:
            raise HTTPException(status_code=404, detail='KNOWLEDGE_DELTA_UNAVAILABLE')
        response.headers['Cache-Control'] = 'no-store'
        return delta
