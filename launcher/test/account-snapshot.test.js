'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { accountSnapshot, createAccountSnapshotPublisher } = require('../account-snapshot');

const identity = id => ({ origin: 'http://127.0.0.1:8080', sessionId: id });
const makeSession = fetchImpl => ({
  status: { authenticated: true, deviceId: 'same-device' },
  knowledgeContext: identity('A'),
  mfaStatus: null,
  featureStatus: fetchImpl,
});
const deferred = () => {
  let resolve;
  const promise = new Promise(res => { resolve = res; });
  return { promise, resolve };
};

test('same account and in-principal token refresh retain current feature grants', async () => {
  const session = makeSession(async () => ({ features: ['companion'] }));
  const result = await accountSnapshot(session);
  assert.deepEqual(result.features, ['companion']);
  assert.equal(result.session.authenticated, true);
});
test('old account feature response never authorizes replacement on same device', async () => {
  const old = deferred();
  const s = makeSession(() => old.promise);
  const pending = accountSnapshot(s);
  s.knowledgeContext = identity('B');
  s.status = { authenticated: true, deviceId: 'same-device' };
  old.resolve({ features: ['owner', 'companion'] });
  const result = await pending;
  assert.deepEqual(result.features, []);
  assert.equal(result.session.authenticated, true);
});
test('logout during pending entitlements never restores signed-in privileges', async () => {
  const old = deferred();
  const s = makeSession(() => old.promise);
  const pending = accountSnapshot(s);
  s.knowledgeContext = null;
  s.status = null;
  old.resolve({ features: ['companion'] });
  assert.deepEqual(await pending, { session: null, features: [], mfa: null });
});
test('provider error does not leak prior entitlements or credentials', async () => {
  const s = makeSession(async () => { throw new Error('secret 123'); });
  assert.deepEqual(await accountSnapshot(s), { session: s.status, features: [], mfa: null });
});
test('missing features and missing principal context deny entitlements', async () => {
  const s = makeSession(async () => ({}));
  assert.deepEqual((await accountSnapshot(s)).features, []);
  s.knowledgeContext = null;
  assert.deepEqual((await accountSnapshot(s)).features, []);
});
test('published account view ignores stale earlier feature response after account switch', async () => {
  const prior = deferred();
  const s = makeSession(() => prior.promise);
  const emitted = [];
  const publisher = createAccountSnapshotPublisher(s, snap => emitted.push(snap));
  const first = publisher.publish();
  s.knowledgeContext = identity('B');
  s.featureStatus = async () => ({ features: ['companion'] });
  assert.equal(await publisher.publish(), true);
  prior.resolve({ features: ['owner'] });
  assert.equal(await first, false);
  assert.deepEqual(emitted.map(x => x.features), [['companion']]);
});
test('explicit logout revokes pending publication without replacement request', async () => {
  const prior = deferred();
  const s = makeSession(() => prior.promise);
  const emitted = [];
  const publisher = createAccountSnapshotPublisher(s, snap => emitted.push(snap));
  const pending = publisher.publish();
  s.status = null;
  s.knowledgeContext = null;
  publisher.revoke();
  prior.resolve({ features: ['companion'] });
  assert.equal(await pending, false);
  assert.deepEqual(emitted, []);
});
test('launcher binds account status IPC, publication and logout to same-generation guard', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(src, /createAccountSnapshotPublisher\(session, snapshot =>/);
  assert.match(src, /accountPublisher\.revoke\(\)/);
  assert.match(src, /void accountPublisher\.publish\(\)/);
  assert.match(src, /accountSnapshot\(session\)/);
});
