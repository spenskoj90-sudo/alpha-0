"""Versioned data-only knowledge packs; no I/O or authorization in evaluation."""
from __future__ import annotations

import hashlib
import math
import os
import re
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr

MAX_PACK_BYTES = 262144
DIGEST = re.compile(r'[0-9a-f]{64}')


class DataModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)


class LocalizedText(DataModel):
    en: str = Field(min_length=1, max_length=2000)
    ru: str = Field(min_length=1, max_length=2000)


class Condition(DataModel):
    signal: str = Field(min_length=1, max_length=128, pattern=r'^[a-zA-Z0-9_.:-]+$')
    op: Literal['eq', 'lt', 'lte', 'gt', 'gte']
    value: StrictBool | StrictInt | StrictFloat | StrictStr


class Rule(DataModel):
    id: str = Field(min_length=1, max_length=128)
    priority: int = Field(ge=0, le=100, strict=True)
    requires: tuple[Condition, ...] = Field(min_length=1, max_length=16)
    text: LocalizedText
    reason: LocalizedText
    provenance: tuple[str, ...] = Field(min_length=1, max_length=16)
    confidence: float | None = Field(default=None, ge=0, le=1, strict=True)


class KnowledgePack(DataModel):
    schema_version: Literal[1]
    id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    game: str = Field(min_length=1, max_length=128)
    platform: Literal['android', 'windows']
    patch: str = Field(min_length=1, max_length=64)
    environment: str = Field(min_length=1, max_length=128)
    profile: str = Field(min_length=1, max_length=128)
    status: Literal['draft', 'validated']
    provenance: tuple[str, ...] = Field(min_length=1, max_length=16)
    revoked: bool
    valid_until_ms: int = Field(gt=0, strict=True)
    max_state_age_ms: int = Field(gt=0, le=30000, strict=True)
    rules: tuple[Rule, ...] = Field(max_length=128)
    coverage: tuple[str, ...] = Field(max_length=64)


@dataclass(frozen=True, slots=True)
class LoadedPack:
    pack: KnowledgePack
    digest: str
    registry: PackRegistry | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Evaluation:
    status: str
    items: tuple[dict, ...] = ()


def load_pack(raw: bytes, expected_digest: str) -> LoadedPack:
    if not raw or len(raw) > MAX_PACK_BYTES: raise ValueError('KNOWLEDGE_SIZE_INVALID')
    if not DIGEST.fullmatch(expected_digest) or hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError('KNOWLEDGE_DIGEST_MISMATCH')
    pack = KnowledgePack.model_validate_json(raw)
    if len({rule.id for rule in pack.rules}) != len(pack.rules): raise ValueError('KNOWLEDGE_DUPLICATE_RULE')
    if any(not s or len(s) > 256 for s in pack.provenance): raise ValueError('KNOWLEDGE_PROVENANCE_INVALID')
    for rule in pack.rules:
        if any(not s or len(s) > 256 for s in rule.provenance): raise ValueError('KNOWLEDGE_PROVENANCE_INVALID')
        if len(set(pack.provenance + rule.provenance)) > 20: raise ValueError('KNOWLEDGE_PROVENANCE_INVALID')
    return LoadedPack(pack, expected_digest)


def matches(condition: Condition, signals: Mapping) -> bool | None:
    value = signals.get(condition.signal)
    expected = condition.value
    if value is None: return None
    if type(expected) is bool:
        return value == expected if type(value) is bool and condition.op == 'eq' else None
    if type(expected) is str:
        return value == expected if type(value) is str and condition.op == 'eq' else None
    if type(value) not in (int, float): return None
    # Huge integers cannot be coerced to a float safely by math.isfinite.
    try:
        if not math.isfinite(value): return None
    except OverflowError:
        return None
    if condition.op == 'eq': return value == expected
    if condition.op == 'lt': return value < expected
    if condition.op == 'lte': return value <= expected
    if condition.op == 'gt': return value > expected
    return value >= expected


def evaluate(loaded: LoadedPack, observation: Mapping, *, now_ms: int, session_id: str, locale: str = 'en') -> Evaluation:
    # Retained cache handles must re-enter their revocation authority on every use.
    if loaded.registry is not None:
        return loaded.registry.evaluate(loaded.digest, observation, now_ms=now_ms, session_id=session_id, locale=locale)
    return _evaluate_data(loaded, observation, now_ms=now_ms, session_id=session_id, locale=locale)


def _evaluate_data(loaded: LoadedPack, observation: Mapping, *, now_ms: int, session_id: str, locale: str = 'en') -> Evaluation:
    pack = loaded.pack
    if type(now_ms) is not int or now_ms <= 0: return Evaluation('stale_state')
    if pack.revoked: return Evaluation('revoked')
    if now_ms >= pack.valid_until_ms: return Evaluation('expired_pack')
    if pack.status != 'validated': return Evaluation('unvalidated_pack')
    for key in ('game', 'platform', 'patch', 'environment', 'profile'):
        if observation.get(key) != getattr(pack, key): return Evaluation('profile_mismatch')
    if not session_id or observation.get('session_id') != session_id: return Evaluation('session_mismatch')
    if observation.get('source_verified') is not True: return Evaluation('source_unverified')
    observed = observation.get('observed_at_ms')
    if type(now_ms) is not int or type(observed) is not int or observed <= 0 or not 0 <= now_ms - observed <= pack.max_state_age_ms:
        return Evaluation('stale_state')
    signals = observation.get('signals')
    if not isinstance(signals, Mapping) or len(signals) > 64: return Evaluation('missing_signals')
    lang = 'ru' if locale == 'ru' else 'en'
    items = []
    missing = False
    for rule in sorted(pack.rules, key=lambda rule: (-rule.priority, rule.id)):
        checks = [matches(condition, signals) for condition in rule.requires]
        missing |= None in checks
        if not all(check is True for check in checks): continue
        items.append({'kind': 'recommendation', 'text': getattr(rule.text, lang), 'reason': getattr(rule.reason, lang), 'priority': rule.priority, 'confidence': rule.confidence, 'provenance': list(dict.fromkeys(pack.provenance + rule.provenance)), 'observed_at_ms': observed, 'engine': 'deterministic', 'pack_digest': loaded.digest, 'rule_id': rule.id})
        if len(items) >= 12: break
    return Evaluation('ready' if items else 'missing_signals' if missing else 'empty', tuple(items))


class PackRegistry:
    """Bounded memory + atomic persistent cache, pinned by trusted distribution digests.

    Not an authorization store. Never construct allowlists from client request data.
    Revocation is durable and takes precedence over an already cached pack.
    """
    def __init__(self, directory: Path, *, allowed_digests: set[str], capacity: int = 16):
        if not 1 <= capacity <= 64 or any(not DIGEST.fullmatch(d) for d in allowed_digests): raise ValueError('KNOWLEDGE_REGISTRY_INVALID')
        self.directory = directory
        self.allowed_digests = frozenset(allowed_digests)
        self.capacity = capacity
        self._cache: OrderedDict[str, LoadedPack] = OrderedDict()
        self._lock = RLock()

    def _allowed(self, digest: str) -> bool:
        return digest in self.allowed_digests and not (self.directory / f'{digest}.revoked').exists()

    def put(self, raw: bytes, digest: str) -> None:
        with self._lock:
            if not self._allowed(digest): raise ValueError('KNOWLEDGE_NOT_ALLOWLISTED')
            loaded = load_pack(raw, digest)
            self.directory.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(dir=self.directory, prefix='.pack-')
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(raw); output.flush(); os.fsync(output.fileno())
                os.replace(temp, self.directory / f'{digest}.json')
            finally:
                if os.path.exists(temp): os.unlink(temp)
            self._remember(digest, loaded)

    def _remember(self, digest: str, loaded: LoadedPack) -> None:
        self._cache[digest] = LoadedPack(loaded.pack, loaded.digest, self)
        self._cache.move_to_end(digest)
        while len(self._cache) > self.capacity: self._cache.popitem(last=False)

    def get(self, digest: str) -> LoadedPack | None:
        with self._lock:
            if not self._allowed(digest): return None
            if digest in self._cache:
                self._cache.move_to_end(digest); return self._cache[digest]
            try:
                path = self.directory / f'{digest}.json'
                if path.stat().st_size > MAX_PACK_BYTES: return None
                loaded = load_pack(path.read_bytes(), digest)
            except (OSError, ValueError): return None
            self._remember(digest, loaded)
            return self._cache[digest]

    def evaluate(self, digest: str, observation: Mapping, *, now_ms: int, session_id: str, locale: str = 'en') -> Evaluation:
        # Serialize same-registry revocation and evaluation. Re-read durable markers
        # before returning, including revocations applied by another registry/process.
        with self._lock:
            if not self._allowed(digest): return Evaluation('revoked')
            loaded = self.get(digest)
            if loaded is None: return Evaluation('unavailable_pack')
            result = _evaluate_data(loaded, observation, now_ms=now_ms, session_id=session_id, locale=locale)
            return result if self._allowed(digest) else Evaluation('revoked')

    def revoke(self, digest: str) -> None:
        with self._lock:
            if digest not in self.allowed_digests: raise ValueError('KNOWLEDGE_NOT_ALLOWLISTED')
            self.directory.mkdir(parents=True, exist_ok=True)
            (self.directory / f'{digest}.revoked').touch()
            self._cache.pop(digest, None)
