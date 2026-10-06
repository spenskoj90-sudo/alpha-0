'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { createHash, randomUUID } = require('node:crypto');
const { performance } = require('node:perf_hooks');

const MAX_BYTES = 262144;
const MAX_STATE_BYTES = 32768;
const MAX_RECORDS = 16;
const MAX_REVOKED = 64;
const PROFILE_KEYS = ['game', 'platform', 'patch', 'environment', 'profile'];
const DIGEST = /^[0-9a-f]{64}$/;

function hash(raw) {
  return createHash('sha256').update(raw).digest('hex');
}

function exact(value, keys) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).length === keys.length &&
    keys.every(key => Object.hasOwn(value, key));
}

function integer(value, min = 0, max = Number.MAX_SAFE_INTEGER) {
  return Number.isSafeInteger(value) && value >= min && value <= max;
}

function nonEmptyString(value, max) {
  return typeof value === 'string' && value.length > 0 && value.length <= max;
}

function validProfile(value) {
  return exact(value, PROFILE_KEYS) &&
    PROFILE_KEYS.every(key => nonEmptyString(value[key], key === 'patch' ? 64 : 128)) &&
    ['android', 'windows'].includes(value.platform);
}

function sameProfile(left, right) {
  return PROFILE_KEYS.every(key => left?.[key] === right?.[key]);
}

function sources(value) {
  return Array.isArray(value) && value.length >= 1 && value.length <= 16 &&
    value.every(item => nonEmptyString(item, 256));
}

function localized(value) {
  return exact(value, ['en', 'ru']) &&
    nonEmptyString(value.en, 2000) && nonEmptyString(value.ru, 2000);
}

function safeConditionValue(value) {
  if (typeof value === 'boolean' || typeof value === 'string') return true;
  return typeof value === 'number' && Number.isFinite(value) &&
    (!Number.isInteger(value) || Number.isSafeInteger(value));
}

function parsePack(raw, expectedDigest, profile) {
  if (!Buffer.isBuffer(raw) || !integer(raw.length, 1, MAX_BYTES) ||
      !DIGEST.test(expectedDigest) || hash(raw) !== expectedDigest) {
    throw new Error('KNOWLEDGE_DIGEST_INVALID');
  }
  if (!validProfile(profile)) throw new Error('KNOWLEDGE_PROFILE_INVALID');

  let pack;
  try { pack = JSON.parse(raw.toString('utf8')); }
  catch { throw new Error('KNOWLEDGE_PACK_INVALID'); }

  const fields = [
    'schema_version', 'id', 'version', ...PROFILE_KEYS, 'status', 'provenance',
    'revoked', 'valid_until_ms', 'max_state_age_ms', 'rules', 'coverage',
  ];
  if (!exact(pack, fields) || pack.schema_version !== 1 ||
      !nonEmptyString(pack.id, 128) || !nonEmptyString(pack.version, 64) ||
      !sameProfile(pack, profile) || pack.status !== 'validated' ||
      pack.revoked !== false || !sources(pack.provenance) ||
      !integer(pack.valid_until_ms, 1) || !integer(pack.max_state_age_ms, 1, 30000) ||
      !Array.isArray(pack.rules) || pack.rules.length > 128 ||
      !Array.isArray(pack.coverage) || pack.coverage.length > 64 ||
      !pack.coverage.every(item => typeof item === 'string' && item.length <= 256)) {
    throw new Error('KNOWLEDGE_PACK_INVALID');
  }
  if (new Set(pack.rules.map(rule => rule?.id)).size !== pack.rules.length) {
    throw new Error('KNOWLEDGE_PACK_INVALID');
  }

  for (const rule of pack.rules) {
    if (rule && !Object.hasOwn(rule, 'confidence')) rule.confidence = null;
    if (!exact(rule, ['id', 'priority', 'requires', 'text', 'reason', 'provenance', 'confidence']) ||
        !nonEmptyString(rule.id, 128) || !integer(rule.priority, 0, 100) ||
        !Array.isArray(rule.requires) || rule.requires.length < 1 || rule.requires.length > 16 ||
        !localized(rule.text) || !localized(rule.reason) || !sources(rule.provenance) ||
        new Set([...pack.provenance, ...rule.provenance]).size > 20 ||
        !(rule.confidence === null ||
          (typeof rule.confidence === 'number' && Number.isFinite(rule.confidence) &&
           rule.confidence >= 0 && rule.confidence <= 1))) {
      throw new Error('KNOWLEDGE_RULE_INVALID');
    }
    for (const condition of rule.requires) {
      if (!exact(condition, ['signal', 'op', 'value']) ||
          !nonEmptyString(condition.signal, 128) ||
          !/^[a-zA-Z0-9_.:-]+$/.test(condition.signal) ||
          !['eq', 'lt', 'lte', 'gt', 'gte'].includes(condition.op) ||
          !safeConditionValue(condition.value) ||
          (typeof condition.value !== 'number' && condition.op !== 'eq')) {
        throw new Error('KNOWLEDGE_CONDITION_INVALID');
      }
    }
  }
  return pack;
}

function strictBase64(value) {
  if (typeof value !== 'string' || value.length > 4 * Math.ceil(MAX_BYTES / 3) ||
      value.length % 4 !== 0 || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)) {
    throw new Error('KNOWLEDGE_DELTA_INVALID');
  }
  const decoded = Buffer.from(value, 'base64');
  if (decoded.toString('base64') !== value) throw new Error('KNOWLEDGE_DELTA_INVALID');
  return decoded;
}

function reconstructDelta(base, envelope, { expectedDigest, profile }) {
  if (!Buffer.isBuffer(base) || !integer(base.length, 1, MAX_BYTES)) {
    throw new Error('KNOWLEDGE_BASE_INVALID');
  }
  const fields = [
    'schema_version', 'algorithm', 'base_digest', 'destination_digest',
    'destination_size', 'prefix_bytes', 'suffix_bytes', 'insert_b64',
  ];
  if (!exact(envelope, fields) || envelope.schema_version !== 1 ||
      envelope.algorithm !== 'byte-splice-v1' ||
      !DIGEST.test(envelope.base_digest) || !DIGEST.test(envelope.destination_digest) ||
      envelope.destination_digest !== expectedDigest || hash(base) !== envelope.base_digest ||
      !integer(envelope.destination_size, 1, MAX_BYTES) ||
      !integer(envelope.prefix_bytes, 0, MAX_BYTES) ||
      !integer(envelope.suffix_bytes, 0, MAX_BYTES) ||
      envelope.prefix_bytes + envelope.suffix_bytes > base.length) {
    throw new Error('KNOWLEDGE_DELTA_INVALID');
  }
  const insert = strictBase64(envelope.insert_b64);
  if (envelope.prefix_bytes + insert.length + envelope.suffix_bytes !== envelope.destination_size) {
    throw new Error('KNOWLEDGE_DELTA_INVALID');
  }
  const tail = envelope.suffix_bytes === 0
    ? Buffer.alloc(0)
    : base.subarray(base.length - envelope.suffix_bytes);
  const destination = Buffer.concat([
    base.subarray(0, envelope.prefix_bytes), insert, tail,
  ]);
  parsePack(destination, expectedDigest, profile);
  return destination;
}

function matches(condition, signals) {
  if (!Object.hasOwn(signals, condition.signal)) return null;
  const actual = signals[condition.signal];
  const expected = condition.value;
  if (typeof actual !== typeof expected) return null;
  if (typeof expected !== 'number') return condition.op === 'eq' ? actual === expected : null;
  if (!Number.isFinite(actual) || (Number.isInteger(actual) && !Number.isSafeInteger(actual))) return null;
  if (condition.op === 'eq') return actual === expected;
  if (condition.op === 'lt') return actual < expected;
  if (condition.op === 'lte') return actual <= expected;
  if (condition.op === 'gt') return actual > expected;
  return actual >= expected;
}

class KnowledgeRuntime {
  #directory;
  #transport;
  #authority;
  #wallClock;
  #monotonicClock;
  #records = {};
  #active = null;
  #epoch = 0;
  #stateInvalid = false;

  constructor({
    directory, transport, authority,
    wallClock = Date.now, monotonicClock = () => performance.now(),
  }) {
    if (!nonEmptyString(directory, 4096) || !transport ||
        !nonEmptyString(authority, 512) || typeof wallClock !== 'function' ||
        typeof monotonicClock !== 'function') {
      throw new Error('KNOWLEDGE_RUNTIME_INVALID');
    }
    this.#directory = directory;
    this.#transport = transport;
    this.#authority = authority;
    this.#wallClock = wallClock;
    this.#monotonicClock = monotonicClock;
    fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
    this.#loadState();
  }

  #loadState() {
    const statePath = path.join(this.#directory, 'state.json');
    try {
      if (fs.statSync(statePath).size > MAX_STATE_BYTES) throw new Error('STATE_SIZE');
      const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
      if (!exact(state, ['authority', 'records']) || state.authority !== this.#authority ||
          state.records === null || typeof state.records !== 'object' ||
          Array.isArray(state.records) || Object.keys(state.records).length > MAX_RECORDS) {
        throw new Error('STATE_INVALID');
      }
      for (const [key, record] of Object.entries(state.records)) {
        if (!DIGEST.test(key) || !exact(record, ['revision', 'digest', 'revoked']) ||
            !integer(record.revision, 1) ||
            !(record.digest === null || DIGEST.test(record.digest)) ||
            !Array.isArray(record.revoked) || record.revoked.length > MAX_REVOKED ||
            !record.revoked.every(value => DIGEST.test(value)) ||
            new Set(record.revoked).size !== record.revoked.length ||
            (record.digest !== null && record.revoked.includes(record.digest))) {
          throw new Error('STATE_INVALID');
        }
      }
      this.#records = state.records;
    } catch (error) {
      if (error?.code !== 'ENOENT') this.#stateInvalid = true;
    }
  }

  #profileKey(profile) {
    return hash(Buffer.from(JSON.stringify([
      this.#authority, ...PROFILE_KEYS.map(key => profile[key]),
    ])));
  }

  #atomicWrite(filename, bytes) {
    const temporary = path.join(this.#directory, `.${randomUUID()}.tmp`);
    let descriptor;
    try {
      descriptor = fs.openSync(temporary, 'wx', 0o600);
      fs.writeFileSync(descriptor, bytes);
      fs.fsyncSync(descriptor);
      fs.closeSync(descriptor);
      descriptor = undefined;
      fs.renameSync(temporary, path.join(this.#directory, filename));
    } finally {
      if (descriptor !== undefined) fs.closeSync(descriptor);
      try { fs.unlinkSync(temporary); } catch (error) { if (error?.code !== 'ENOENT') throw error; }
    }
  }

  #persist(key, record) {
    if (!Object.hasOwn(this.#records, key) && Object.keys(this.#records).length >= MAX_RECORDS) {
      throw new Error('KNOWLEDGE_CACHE_BOUND');
    }
    const records = { ...this.#records, [key]: record };
    const raw = Buffer.from(JSON.stringify({ authority: this.#authority, records }));
    if (raw.length > MAX_STATE_BYTES) throw new Error('KNOWLEDGE_CACHE_BOUND');
    this.#atomicWrite('state.json', raw);
    this.#records = records;
  }

  async #trusted(operation, epoch) {
    try { return await operation(); }
    catch (error) {
      if (epoch === this.#epoch &&
          ['AUTHENTICATION_REQUIRED', 'KNOWLEDGE_ACCESS_DENIED'].includes(error?.message)) {
        this.clear();
      }
      throw error;
    }
  }

  #cachedBytes(digest, profile) {
    const filename = path.join(this.#directory, `${digest}.json`);
    try {
      if (fs.statSync(filename).size > MAX_BYTES) return null;
      const raw = fs.readFileSync(filename);
      parsePack(raw, digest, profile);
      return raw;
    } catch { return null; }
  }

  clear() {
    this.#epoch += 1;
    this.#active = null;
  }

  status() {
    if (!this.#active) {
      return { status: 'unavailable_pack', digest: null, remainingLeaseMs: null, actionAuthority: false };
    }
    const now = this.#monotonicClock();
    const wall = this.#wallClock();
    const valid = Number.isFinite(now) && now >= this.#active.started && now < this.#active.deadline &&
      integer(wall, 1) && wall < this.#active.pack.valid_until_ms;
    return {
      status: valid ? 'ready' : 'expired_lease',
      digest: this.#active.digest,
      remainingLeaseMs: valid ? Math.max(0, Math.floor(this.#active.deadline - now)) : 0,
      actionAuthority: false,
    };
  }

  async refresh(profile, sessionId) {
    if (this.#stateInvalid) throw new Error('KNOWLEDGE_STATE_INVALID');
    if (!validProfile(profile) || !nonEmptyString(sessionId, 256)) {
      throw new Error('KNOWLEDGE_PROFILE_SESSION_INVALID');
    }
    const key = this.#profileKey(profile);
    if (this.#active && (this.#active.key !== key || this.#active.sessionId !== sessionId)) this.clear();
    const epoch = ++this.#epoch;
    const started = this.#monotonicClock();
    const previous = this.#records[key];
    const manifest = await this.#trusted(
      () => this.#transport.manifest(profile, previous?.digest || null), epoch,
    );
    if (epoch !== this.#epoch) throw new Error('KNOWLEDGE_SESSION_CHANGED');
    this.#validateManifest(manifest, profile);

    if (previous && manifest.revision < previous.revision) {
      this.#active = null;
      throw new Error('KNOWLEDGE_REVISION_ROLLBACK');
    }
    if (manifest.status === 'revoked' || manifest.status === 'unavailable') {
      this.#active = null;
      if (manifest.revision > 0) {
        const revoked = [...(previous?.revoked || [])];
        if (manifest.status === 'revoked') {
          if (!DIGEST.test(manifest.digest)) throw new Error('KNOWLEDGE_MANIFEST_INVALID');
          if (!revoked.includes(manifest.digest)) revoked.push(manifest.digest);
        }
        if (revoked.length > MAX_REVOKED) throw new Error('KNOWLEDGE_CACHE_BOUND');
        this.#persist(key, { revision: manifest.revision, digest: null, revoked });
      }
      return { status: manifest.status, items: [], actionAuthority: false };
    }

    if (!DIGEST.test(manifest.digest) || !integer(manifest.revision, 1) ||
        !nonEmptyString(manifest.version, 64) ||
        !integer(manifest.lease_until_ms, manifest.server_time_ms + 1,
          manifest.server_time_ms + 60000) ||
        previous?.revoked.includes(manifest.digest) ||
        (previous && manifest.revision === previous.revision && previous.digest !== manifest.digest)) {
      throw new Error('KNOWLEDGE_REVOKED_OR_INVALID_REVISION');
    }

    let raw = this.#cachedBytes(manifest.digest, profile);
    if (!raw && previous?.digest && previous.digest !== manifest.digest) {
      const base = this.#cachedBytes(previous.digest, profile);
      if (base) {
        try {
          const envelope = await this.#trusted(
            () => this.#transport.delta(profile, manifest.digest, previous.digest), epoch,
          );
          if (epoch !== this.#epoch) throw new Error('KNOWLEDGE_SESSION_CHANGED');
          raw = reconstructDelta(base, envelope, { expectedDigest: manifest.digest, profile });
        } catch (error) {
          if (error?.message !== 'KNOWLEDGE_DELTA_UNAVAILABLE') {
            if (['AUTHENTICATION_REQUIRED', 'KNOWLEDGE_ACCESS_DENIED',
              'KNOWLEDGE_SESSION_CHANGED'].includes(error?.message)) throw error;
            if (String(error?.message || '').startsWith('KNOWLEDGE_')) {
              throw new Error('KNOWLEDGE_DELTA_INVALID');
            }
            throw error;
          }
        }
      }
    }
    if (!raw) {
      raw = await this.#trusted(() => this.#transport.pack(profile, manifest.digest), epoch);
    }
    if (epoch !== this.#epoch) throw new Error('KNOWLEDGE_SESSION_CHANGED');
    const pack = parsePack(raw, manifest.digest, profile);
    if (pack.version !== manifest.version || pack.valid_until_ms < manifest.lease_until_ms) {
      throw new Error('KNOWLEDGE_LEASE_INVALID');
    }
    const elapsed = this.#monotonicClock() - started;
    const leaseDuration = manifest.lease_until_ms - manifest.server_time_ms;
    if (!Number.isFinite(started) || !Number.isFinite(elapsed) || elapsed < 0 || elapsed >= leaseDuration) {
      throw new Error('KNOWLEDGE_LEASE_EXPIRED');
    }

    this.#atomicWrite(`${manifest.digest}.json`, raw);
    this.#persist(key, {
      revision: manifest.revision, digest: manifest.digest, revoked: previous?.revoked || [],
    });
    this.#active = {
      key, sessionId, profile: { ...profile }, pack, digest: manifest.digest,
      started, serverTime: manifest.server_time_ms, deadline: started + leaseDuration,
    };
    this.#removeUnreferencedBytes();
    return {
      status: 'ready', digest: manifest.digest, revision: manifest.revision, actionAuthority: false,
    };
  }

  #validateManifest(manifest, profile) {
    const fields = [
      'schema_version', 'status', 'profile', 'revision', 'digest', 'version',
      'lease_until_ms', 'server_time_ms', 'execution_authority',
    ];
    if (!exact(manifest, fields) || manifest.schema_version !== 1 ||
        !validProfile(manifest.profile) || !sameProfile(manifest.profile, profile) ||
        !integer(manifest.revision) || !integer(manifest.server_time_ms, 1) ||
        manifest.execution_authority !== false ||
        !['available', 'unchanged', 'revoked', 'unavailable'].includes(manifest.status)) {
      throw new Error('KNOWLEDGE_MANIFEST_INVALID');
    }
  }

  #removeUnreferencedBytes() {
    const referenced = new Set(Object.values(this.#records)
      .map(record => record.digest)
      .filter(Boolean));
    for (const entry of fs.readdirSync(this.#directory)) {
      if (/^[0-9a-f]{64}\.json$/.test(entry) && !referenced.has(entry.slice(0, -5))) {
        fs.unlinkSync(path.join(this.#directory, entry));
      }
    }
  }

  evaluate(observation, { sessionId, locale = 'en' } = {}) {
    const denied = status => ({ status, items: [] });
    const active = this.#active;
    if (!active) return denied('unavailable_pack');
    const monotonic = this.#monotonicClock();
    const wall = this.#wallClock();
    if (!Number.isFinite(monotonic) || monotonic < active.started || monotonic >= active.deadline ||
        !integer(wall, 1)) return denied('expired_lease');
    const now = Math.max(wall, active.serverTime + monotonic - active.started);
    if (now >= active.pack.valid_until_ms) return denied('expired_pack');
    if (!sameProfile(observation, active.profile)) return denied('profile_mismatch');
    if (sessionId !== active.sessionId || observation?.session_id !== sessionId) {
      return denied('session_mismatch');
    }
    if (observation?.source_verified !== true) return denied('source_unverified');
    if (!integer(observation?.observed_at_ms, 1)) return denied('stale_state');
    if (observation.observed_at_ms > now) return denied('future_state');
    if (now - observation.observed_at_ms > active.pack.max_state_age_ms) return denied('stale_state');
    const signals = observation.signals;
    if (signals === null || typeof signals !== 'object' || Array.isArray(signals) ||
        Object.keys(signals).length > 64) return denied('missing_signals');

    const language = locale === 'ru' ? 'ru' : 'en';
    const items = [];
    let missing = false;
    for (const rule of [...active.pack.rules]
      .sort((left, right) => right.priority - left.priority || left.id.localeCompare(right.id))) {
      const checks = rule.requires.map(condition => matches(condition, signals));
      if (checks.includes(null)) missing = true;
      if (!checks.every(value => value === true)) continue;
      items.push({
        kind: 'recommendation', text: rule.text[language], reason: rule.reason[language],
        priority: rule.priority, confidence: rule.confidence,
        provenance: [...new Set([...active.pack.provenance, ...rule.provenance])],
        observed_at_ms: observation.observed_at_ms, engine: 'deterministic',
        pack_digest: active.digest, rule_id: rule.id,
      });
      if (items.length >= 12) break;
    }
    return { status: items.length ? 'ready' : missing ? 'missing_signals' : 'empty', items };
  }
}

module.exports = {
  MAX_BYTES,
  KnowledgeRuntime,
  parsePack,
  reconstructDelta,
  validProfile,
};
