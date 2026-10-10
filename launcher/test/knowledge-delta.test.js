'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { reconstructDelta } = require('../knowledge-runtime');
const { profile, packBytes, manifestFor, setup } = require('./knowledge-fixture');

function delta(base, destination, changes = {}) {
  let prefix = 0;
  const bound = Math.min(base.length, destination.length);
  while (prefix < bound && base[prefix] === destination[prefix]) prefix += 1;
  let suffix = 0;
  while (suffix < bound - prefix && base[base.length - suffix - 1] === destination[destination.length - suffix - 1]) suffix += 1;
  const end = destination.length - suffix;
  return {
    schema_version: 1, algorithm: 'byte-splice-v1',
    base_digest: createHash('sha256').update(base).digest('hex'),
    destination_digest: createHash('sha256').update(destination).digest('hex'),
    destination_size: destination.length,
    prefix_bytes: prefix, suffix_bytes: suffix,
    insert_b64: destination.subarray(prefix, end).toString('base64'),
    ...changes,
  };
}

test('byte-splice reconstruction validates the complete destination pack', () => {
  const base = packBytes();
  const destination = packBytes({ version: '2' });
  const rebuilt = reconstructDelta(base.raw, delta(base.raw, destination.raw), {
    expectedDigest: destination.digest, profile,
  });
  assert.deepEqual(rebuilt, destination.raw);

  const malformed = [
    delta(base.raw, destination.raw, { schema_version: true }),
    delta(base.raw, destination.raw, { destination_size: destination.raw.length + 1 }),
    delta(base.raw, destination.raw, { prefix_bytes: base.raw.length, suffix_bytes: 1 }),
    delta(base.raw, destination.raw, { insert_b64: '***' }),
    delta(base.raw, destination.raw, { destination_digest: 'a'.repeat(64) }),
  ];
  for (const envelope of malformed) {
    assert.throws(() => reconstructDelta(base.raw, envelope, {
      expectedDigest: destination.digest, profile,
    }), /KNOWLEDGE_/);
  }
});

test('refresh uses a validated delta from installed base and does not fetch full bytes', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  const destination = packBytes({ version: '2' });
  state.setManifest(manifestFor(destination, { revision: 2, version: '2' }));
  state.transport.delta = async (_profile, digest, baseDigest) => {
    state.calls.delta += 1;
    assert.equal(digest, destination.digest);
    assert.equal(baseDigest, state.value.digest);
    return delta(state.value.raw, destination.raw);
  };
  state.setRaw(Buffer.from('{}'));
  const result = await state.runtime.refresh(profile, 'session-a');
  assert.deepEqual(result, { status: 'ready', digest: destination.digest, revision: 2, actionAuthority: false });
  assert.equal(state.calls.delta, 1);
  assert.equal(state.calls.pack, 1);
});

test('unavailable delta falls back to full bytes but malformed delta never does', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  const destination = packBytes({ version: '2' });
  state.setManifest(manifestFor(destination, { revision: 2, version: '2' }));
  state.setRaw(destination.raw);

  await state.runtime.refresh(profile, 'session-a');
  assert.equal(state.calls.delta, 1);
  assert.equal(state.calls.pack, 2);

  const third = packBytes({ version: '3' });
  state.setManifest(manifestFor(third, { revision: 3, version: '3' }));
  state.transport.delta = async () => delta(destination.raw, third.raw, { insert_b64: '***' });
  await assert.rejects(state.runtime.refresh(profile, 'session-a'), /KNOWLEDGE_DELTA_INVALID/);
  assert.equal(state.calls.pack, 2);
  assert.equal(state.runtime.status().digest, destination.digest);
});

test('access denial during delta fetch clears the active lease and keeps its terminal code', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  const destination = packBytes({ version: '2' });
  state.setManifest(manifestFor(destination, { revision: 2, version: '2' }));
  state.transport.delta = async () => { throw new Error('KNOWLEDGE_ACCESS_DENIED'); };
  await assert.rejects(state.runtime.refresh(profile, 'session-a'), /KNOWLEDGE_ACCESS_DENIED/);
  assert.equal(state.runtime.status().status, 'unavailable_pack');
});
