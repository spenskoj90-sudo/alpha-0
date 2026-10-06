'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { KnowledgeRuntime, parsePack } = require('../knowledge-runtime');
const { profile, packBytes, manifestFor, setup } = require('./knowledge-fixture');

function observation(changes = {}) {
  return {
    ...profile, session_id: 'session-a', source_verified: true,
    observed_at_ms: 1500, signals: { health: 0.2 }, ...changes,
  };
}

test('validated bytes produce deterministic presentation only', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  const result = state.runtime.evaluate(observation(), { sessionId: 'session-a', locale: 'ru' });
  assert.equal(result.status, 'ready');
  assert.equal(result.items.length, 1);
  assert.deepEqual(result.items[0], {
    kind: 'recommendation', text: 'Проверьте защиту', reason: 'Сниженное здоровье',
    priority: 10, confidence: null,
    provenance: ['fixture:review', 'fixture:rule'], observed_at_ms: 1500,
    engine: 'deterministic', pack_digest: state.value.digest, rule_id: 'defensive',
  });
  assert.equal(result.items[0].execute, undefined);
  assert.equal(state.runtime.status().actionAuthority, false);
});

test('profile, session, source and time mismatches deny presentation', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  const cases = [
    observation({ patch: '2' }),
    observation({ session_id: 'session-b' }),
    observation({ source_verified: false }),
    observation({ observed_at_ms: 2500 }),
    observation({ signals: { health: true } }),
  ];
  const statuses = cases.map(value => state.runtime.evaluate(value, { sessionId: 'session-a' }).status);
  assert.deepEqual(statuses, ['profile_mismatch', 'session_mismatch', 'source_unverified', 'future_state', 'missing_signals']);
  for (const value of cases) assert.deepEqual(state.runtime.evaluate(value, { sessionId: 'session-a' }).items, []);
});

test('wall-clock rollback cannot extend the monotonic lease', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  state.advance(1000, 60011);
  assert.deepEqual(state.runtime.status(), {
    status: 'expired_lease', digest: state.value.digest, remainingLeaseMs: 0, actionAuthority: false,
  });
  assert.equal(state.runtime.evaluate(observation({ observed_at_ms: 1000 }), { sessionId: 'session-a' }).status, 'expired_lease');
});

test('revocation is durable and an older manifest cannot restore the digest', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  state.setManifest(manifestFor(state.value, {
    status: 'revoked', revision: 2, lease_until_ms: null,
  }));
  assert.equal((await state.runtime.refresh(profile, 'session-a')).status, 'revoked');
  assert.equal(state.runtime.evaluate(observation(), { sessionId: 'session-a' }).status, 'unavailable_pack');

  const restarted = new KnowledgeRuntime({
    directory: state.directory, transport: state.transport, authority: 'fixture-origin',
    wallClock: () => 1500, monotonicClock: () => 10,
  });
  state.setManifest(manifestFor(state.value));
  await assert.rejects(restarted.refresh(profile, 'session-a'), /REVISION_ROLLBACK|REVOKED/);
  assert.equal(restarted.status().status, 'unavailable_pack');
});

test('corrupt durable metadata fails closed even when valid bytes remain', async t => {
  const state = setup(t);
  await state.runtime.refresh(profile, 'session-a');
  fs.writeFileSync(path.join(state.directory, 'state.json'), '{}');
  const restarted = new KnowledgeRuntime({
    directory: state.directory, transport: state.transport, authority: 'fixture-origin',
  });
  await assert.rejects(restarted.refresh(profile, 'session-a'), /KNOWLEDGE_STATE_INVALID/);
  assert.equal(restarted.status().status, 'unavailable_pack');
});

test('clear during an in-flight manifest prevents late installation', async t => {
  const state = setup(t);
  let complete;
  state.transport.manifest = () => new Promise(resolve => { complete = resolve; });
  const pending = state.runtime.refresh(profile, 'session-a');
  state.runtime.clear();
  complete(manifestFor(state.value));
  await assert.rejects(pending, /KNOWLEDGE_SESSION_CHANGED/);
  assert.equal(state.runtime.status().status, 'unavailable_pack');
  assert.equal(state.calls.pack, 0);
});

test('pack validator rejects executable fields and unsafe numeric thresholds', () => {
  for (const changes of [
    { executor: 'input' },
    { rules: [{
      id: 'unsafe', priority: 1,
      requires: [{ signal: 'health', op: 'eq', value: Number.MAX_SAFE_INTEGER + 1 }],
      text: { en: 'Unsafe', ru: 'Опасно' }, reason: { en: 'Unsafe', ru: 'Опасно' },
      provenance: ['fixture:rule'], confidence: null,
    }] },
  ]) {
    const value = packBytes(changes);
    assert.throws(() => parsePack(value.raw, value.digest, profile), /KNOWLEDGE_(PACK|CONDITION)_INVALID/);
  }
});
