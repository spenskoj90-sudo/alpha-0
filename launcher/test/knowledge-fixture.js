'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { KnowledgeRuntime } = require('../knowledge-runtime');

const profile = Object.freeze({
  game: 'fixture', platform: 'windows', patch: '1', environment: 'offline-fixture', profile: 'tank',
});

function packBytes(changes = {}) {
  const pack = {
    schema_version: 1,
    id: 'fixture',
    version: '1',
    ...profile,
    status: 'validated',
    provenance: ['fixture:review'],
    revoked: false,
    valid_until_ms: 100000,
    max_state_age_ms: 1000,
    rules: [{
      id: 'defensive', priority: 10,
      requires: [{ signal: 'health', op: 'lte', value: 0.3 }],
      text: { en: 'Review defense', ru: 'Проверьте защиту' },
      reason: { en: 'Low health', ru: 'Сниженное здоровье' },
      provenance: ['fixture:rule'], confidence: null,
    }],
    coverage: ['defensive'],
    ...changes,
  };
  const raw = Buffer.from(JSON.stringify(pack));
  return { raw, digest: createHash('sha256').update(raw).digest('hex'), pack };
}

function manifestFor(value, changes = {}) {
  return {
    schema_version: 1, status: 'available', profile, revision: 1,
    digest: value.digest, version: value.pack.version,
    lease_until_ms: 61500, server_time_ms: 1500,
    execution_authority: false,
    ...changes,
  };
}

function setup(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-knowledge-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const value = packBytes();
  let wall = 1500;
  let monotonic = 10;
  let manifest = manifestFor(value);
  let raw = value.raw;
  const calls = { pack: 0, delta: 0 };
  const transport = {
    manifest: async () => structuredClone(manifest),
    pack: async () => { calls.pack += 1; return Buffer.from(raw); },
    delta: async () => { calls.delta += 1; throw new Error('KNOWLEDGE_DELTA_UNAVAILABLE'); },
  };
  const runtime = new KnowledgeRuntime({
    directory, transport, authority: 'fixture-origin',
    wallClock: () => wall, monotonicClock: () => monotonic,
  });
  return {
    value, directory, runtime, transport, calls,
    setManifest(next) { manifest = next; },
    setRaw(next) { raw = next; },
    advance(nextWall, nextMonotonic) { wall = nextWall; monotonic = nextMonotonic; },
  };
}

module.exports = { profile, packBytes, manifestFor, setup };
