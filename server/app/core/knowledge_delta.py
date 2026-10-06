"""Bounded byte-splice transport; destination authority comes from a trusted manifest."""
from __future__ import annotations

import base64
import binascii
import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.knowledge_packs import MAX_PACK_BYTES, load_pack


class PackDelta(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    schema_version: Literal[1]
    algorithm: Literal['byte-splice-v1']
    base_digest: str = Field(pattern=r'^[0-9a-f]{64}$')
    destination_digest: str = Field(pattern=r'^[0-9a-f]{64}$')
    destination_size: int = Field(ge=1, le=MAX_PACK_BYTES)
    prefix_bytes: int = Field(ge=0, le=MAX_PACK_BYTES)
    suffix_bytes: int = Field(ge=0, le=MAX_PACK_BYTES)
    insert_b64: str = Field(max_length=4 * ((MAX_PACK_BYTES + 2) // 3))

    @field_validator('schema_version', mode='before')
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('KNOWLEDGE_DELTA_SCHEMA_INVALID')
        return value


def _bounded(raw: bytes) -> None:
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_PACK_BYTES:
        raise ValueError('KNOWLEDGE_SIZE_INVALID')


def make_delta(base: bytes, destination: bytes) -> dict:
    _bounded(base)
    _bounded(destination)
    prefix = 0
    bound = min(len(base), len(destination))
    while prefix < bound and base[prefix] == destination[prefix]:
        prefix += 1
    suffix = 0
    while suffix < bound - prefix and base[-suffix - 1] == destination[-suffix - 1]:
        suffix += 1
    end = len(destination) - suffix
    return PackDelta(schema_version=1, algorithm='byte-splice-v1',
                     base_digest=hashlib.sha256(base).hexdigest(),
                     destination_digest=hashlib.sha256(destination).hexdigest(),
                     destination_size=len(destination), prefix_bytes=prefix, suffix_bytes=suffix,
                     insert_b64=base64.b64encode(destination[prefix:end]).decode('ascii')).model_dump()


def reconstruct_delta(base: bytes, envelope: dict, *, expected_digest: str) -> bytes:
    """Caller installs only after this returns; this does not change a cache or lease."""
    _bounded(base)
    delta = PackDelta.model_validate(envelope)
    if delta.destination_digest != expected_digest:
        raise ValueError('KNOWLEDGE_DIGEST_MISMATCH')
    if hashlib.sha256(base).hexdigest() != delta.base_digest:
        raise ValueError('KNOWLEDGE_BASE_MISMATCH')
    if delta.prefix_bytes + delta.suffix_bytes > len(base):
        raise ValueError('KNOWLEDGE_SPLICE_INVALID')
    try:
        insert = base64.b64decode(delta.insert_b64, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError('KNOWLEDGE_SPLICE_INVALID') from None
    if delta.prefix_bytes + len(insert) + delta.suffix_bytes != delta.destination_size:
        raise ValueError('KNOWLEDGE_SIZE_INVALID')
    tail = base[len(base) - delta.suffix_bytes:] if delta.suffix_bytes else b''
    destination = base[:delta.prefix_bytes] + insert + tail
    load_pack(destination, expected_digest)
    return destination
