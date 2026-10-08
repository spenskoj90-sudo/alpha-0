'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { KnowledgePresentation } = require('../knowledge-presentation');
const { profile, setup } = require('./knowledge-fixture');

function harness(t) {
  const state = setup(t);
  let verified = { profile, sourceId: 'fixture-capture' };
  let authenticated = true;
  let cancellations = 0;
  const session = {
    get knowledgeContext() { return authenticated ? { origin: 'fixture-origin', sessionId: 'session-a' } : null; },
    cancelKnowledge() { cancellations += 1; },
  };
  const controller = new KnowledgePresentation({ directory: state.directory, session,
    getTrustedContext: () => verified,
    getTrustedObservation: () => ({ sourceId: 'fixture-capture', observation: {
      ...profile, session_id: 'session-a', source_verified: true,
      observed_at_ms: 1500, signals: { health: 0.2 },
    } }),
    createRuntime: () => state.runtime,
  });
  t.after(() => controller.stop());
  return { ...state, controller, setVerified(value) { verified = value; },
    signOut() { authenticated = false; }, get cancellations() { return cancellations; } };
}

test('shipped missing profile never trusts renderer assertions or fetches distribution', async t => {
  const h = harness(t);
  h.setVerified(null);
  assert.equal(h.controller.status().state, 'STOPPED');
  await h.controller.start({ profile, source_verified: true });
  assert.equal(h.controller.status().state, 'WAITING_FOR_VERIFIED_PROFILE');
  assert.equal(h.calls.pack, 0);
  assert.deepEqual(h.controller.presentations(), []);
  assert.equal(h.controller.status().actionAuthority, false);
  h.signOut(); h.controller.logout();
  assert.equal(h.controller.status().state, 'SIGNED_OUT');
});

test('trusted closure grants bounded presentation and Stop clears it synchronously', async t => {
  const h = harness(t);
  await h.controller.start();
  assert.equal(h.controller.status().state, 'READY');
  assert.equal(h.controller.presentations().length, 1);
  h.controller.stop();
  assert.deepEqual(h.controller.presentations(), []);
  assert.equal(h.controller.status().state, 'STOPPED');
  assert.ok(h.cancellations > 0);
});

test('late fetch after Stop cannot install or renew presentation', async t => {
  const h = harness(t);
  let finish;
  h.transport.pack = () => new Promise(resolve => { finish = resolve; });
  const pending = h.controller.start();
  await new Promise(resolve => setImmediate(resolve));
  h.controller.stop();
  finish(h.value.raw);
  await pending;
  assert.deepEqual(h.controller.presentations(), []);
  assert.equal(h.runtime.status().digest, null);
});

test('access denial clears a prior lease; transient network retains only its existing lease', async t => {
  const h = harness(t);
  await h.controller.start();
  h.transport.manifest = async () => { throw new Error('KNOWLEDGE_NETWORK_ERROR'); };
  await h.controller.refresh();
  assert.equal(h.controller.status().state, 'DEGRADED');
  assert.equal(h.controller.presentations().length, 1);
  h.transport.manifest = async () => { throw new Error('KNOWLEDGE_ACCESS_DENIED'); };
  await h.controller.refresh();
  assert.equal(h.controller.status().state, 'DENIED');
  assert.deepEqual(h.controller.presentations(), []);
});

test('trusted source replacement invalidates old presentation before fetching', async t => {
  const h = harness(t);
  await h.controller.start();
  h.setVerified({ profile, sourceId: 'different-capture' });
  assert.deepEqual(h.controller.presentations(), []);
  assert.equal(h.controller.status().state, 'WAITING_FOR_VERIFIED_PROFILE');
  h.setVerified(null);
  await h.controller.refresh();
  assert.equal(h.controller.status().state, 'WAITING_FOR_VERIFIED_PROFILE');
  assert.deepEqual(h.controller.presentations(), []);
});

test('cache construction failures become a safe unavailable state', async t => {
  const h = harness(t);
  const controller = new KnowledgePresentation({ directory: h.directory, session: {
    knowledgeContext: { origin: 'fixture-origin', sessionId: 'session-a' }, cancelKnowledge() {},
  }, getTrustedContext: () => ({ profile, sourceId: 'capture' }), getTrustedObservation: () => null,
  createRuntime() { throw new Error('EACCES'); } });
  t.after(() => controller.stop());
  await controller.start();
  assert.equal(controller.status().state, 'UNAVAILABLE');
  assert.deepEqual(controller.presentations(), []);
});

test('periodic renewal is bounded and Stop removes its timer', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const h = harness(t);
  let reads = 0;
  const manifest = h.transport.manifest;
  h.transport.manifest = async (...args) => { reads += 1; return manifest(...args); };
  await h.controller.start();
  assert.equal(reads, 1);
  t.mock.timers.tick(30000);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(reads, 2);
  h.controller.stop();
  t.mock.timers.tick(60000);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(reads, 2);
});
