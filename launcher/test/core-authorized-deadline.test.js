'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { CoreSessionManager } = require('../core-session');

const reply = (status, value) => ({
  status, ok: status >= 200 && status < 300, json: async () => value,
});
const credentials = {
  session_token: 'synthetic-access-token', refresh_token: 'synthetic-refresh-token',
  expires_at: '2030-01-01T00:00:00Z', scopes: ['game:read'],
};
const create = (fetchImpl, coreTimeoutMs = 50) =>
  new CoreSessionManager({ fetchImpl, coreTimeoutMs, knowledgeTimeoutMs: 100 });

async function login(manager) {
  return manager.login({
    coreUrl: 'http://127.0.0.1:8080', email: 'test@example.test', password: 'synthetic',
  });
}

test('authorized feature request has a finite total deadline even if fetch ignores AbortSignal', async () => {
  let signal;
  const manager = create((url, init) => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    signal = init.signal;
    return new Promise(() => {});
  }, 30);
  await login(manager);
  await assert.rejects(manager.featureStatus(), /CORE_REQUEST_TIMEOUT/);
  assert.equal(signal.aborted, true);
  assert.equal(manager.status.authenticated, true);
});

test('logout aborts an in-flight feature lookup without waiting for the server', async () => {
  let signal;
  const manager = create((url, init) => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    signal = init.signal;
    return new Promise(() => {});
  }, 250);
  await login(manager);
  const pending = manager.featureStatus();
  manager.clear();
  await assert.rejects(pending, /SESSION_CHANGED/);
  assert.equal(signal.aborted, true);
  assert.equal(manager.accessToken, null);
});

test('response JSON decoding shares the deadline and cannot hang the voice UI', async () => {
  let signal;
  const manager = create((url, init) => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    signal = init.signal;
    return Promise.resolve({ status: 200, ok: true, json: () => new Promise(() => {}) });
  }, 30);
  await login(manager);
  await assert.rejects(manager.voiceStatus(), /CORE_REQUEST_TIMEOUT/);
  assert.equal(signal.aborted, true);
});

test('deadline is total across unauthorized response and refresh retry', async () => {
  const paths = [];
  const manager = create((url, init) => {
    paths.push({ url, signal: init.signal });
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    if (url.endsWith('/v1/billing/features')) return Promise.resolve(reply(401, { code: 'EXPIRED' }));
    if (url.endsWith('/v1/sessions/refresh')) return new Promise(() => {});
    throw new Error('UNEXPECTED_ROUTE');
  }, 30);
  await login(manager);
  await assert.rejects(manager.featureStatus(), /CORE_REQUEST_TIMEOUT/);
  assert.equal(paths.filter(x => x.url.endsWith('/v1/sessions/refresh')).length, 1);
  assert.equal(manager.status.authenticated, true);
});

test('cancelled pending voice result cannot resurrect authorization after logout', async () => {
  let resolvePending;
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    return new Promise(resolve => { resolvePending = resolve; });
  }, 200);
  await login(manager);
  const pending = manager.transcribeVoice({
    audioBase64: 'YQ==', locale: 'en', recommendationId: null, consentGranted: true,
  });
  manager.clear();
  resolvePending(reply(200, { accepted: true, transcript: 'stale' }));
  await assert.rejects(pending, /SESSION_CHANGED/);
  assert.equal(manager.status, null);
});

test('successful feature and voice requests preserve their normal responses', async () => {
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    if (url.endsWith('/v1/billing/features')) return Promise.resolve(reply(200, { features: ['companion'] }));
    if (url.endsWith('/v1/companion/voice/status')) return Promise.resolve(reply(200, { sttAvailable: true }));
    throw new Error('UNEXPECTED_ROUTE');
  });
  await login(manager);
  assert.deepEqual(await manager.featureStatus(), { features: ['companion'] });
  assert.deepEqual(await manager.voiceStatus(), { sttAvailable: true });
});

test('invalid request-deadline parameters fail before any transport activity', () => {
  for (const value of [0, -1, NaN, 1.5, 30001, '10', null]) {
    assert.throws(() => create(() => {}, value), /CORE_TIMEOUT_INVALID/);
  }
});
