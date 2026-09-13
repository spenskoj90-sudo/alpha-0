'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { CoreSessionManager, normalizeCoreUrl } = require('../core-session');
const { CompanionProcessManager, sanitizeStatus } = require('../companion-process');
const { ReconnectPolicy, authProtocols, websocketUrl } = require('../companion-worker');

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test('CoreSessionManager keeps opaque tokens out of renderer-visible status', async () => {
  const calls = [];
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, init });
      if (url.endsWith('/v1/auth/login')) {
        return response(200, {
          session_token: 'access-token-0123456789',
          refresh_token: 'refresh-token-0123456789',
          expires_at: '2026-09-13T10:00:00Z',
          scopes: ['billing:read'],
        });
      }
      return response(200, { features: ['companion'] });
    },
  });

  const status = await manager.login({ coreUrl: 'http://127.0.0.1:8080/', email: 'user@example.com', password: 'secret' });
  assert.deepEqual(status, {
    authenticated: true,
    expiresAt: '2026-09-13T10:00:00Z',
    scopes: ['billing:read'],
  });
  assert.equal(JSON.stringify(status).includes('access-token'), false);
  assert.equal(manager.accessToken, 'access-token-0123456789');
  assert.equal(manager.coreUrl, 'http://127.0.0.1:8080');
  assert.equal(calls[0].url, 'http://127.0.0.1:8080/v1/auth/login');
});

test('refresh rotates both opaque tokens and invalid refresh clears session', async () => {
  let refreshCount = 0;
  const manager = new CoreSessionManager({
    fetchImpl: async url => {
      if (url.endsWith('/v1/auth/login')) {
        return response(200, { session_token: 'access-old-0123456789', refresh_token: 'refresh-old-0123456789', scopes: [] });
      }
      refreshCount += 1;
      if (refreshCount === 1) return response(200, { session_token: 'access-new-0123456789', refresh_token: 'refresh-new-0123456789', scopes: [] });
      return response(401, { detail: 'INVALID_REFRESH_TOKEN' });
    },
  });
  await manager.login({ coreUrl: 'http://localhost:8080', email: 'u@example.com', password: 'p' });
  await manager.refresh();
  assert.equal(manager.accessToken, 'access-new-0123456789');
  assert.equal(manager.refreshToken, 'refresh-new-0123456789');
  await assert.rejects(manager.refresh(), /INVALID_REFRESH_TOKEN/);
  assert.equal(manager.status, null);
  assert.equal(manager.accessToken, null);
});

test('companion auth uses subprotocol instead of URL and only loopback Core is allowed', () => {
  const token = 'opaque-session-token-0123456789';
  const protocols = authProtocols(token);
  assert.equal(protocols[0], 'sentinel.v1');
  assert.match(protocols[1], /^sentinel\.auth\.[A-Za-z0-9_-]+$/);
  assert.equal(protocols.join(',').includes(token), false);
  const url = websocketUrl('http://127.0.0.1:8080');
  assert.equal(url, 'ws://127.0.0.1:8080/v1/companion/ws');
  assert.equal(url.includes(token), false);
  assert.throws(() => websocketUrl('https://core.example.com'), /COMPANION_CORE_MUST_BE_LOOPBACK/);
  assert.throws(() => normalizeCoreUrl('file:///tmp/core'), /INVALID_CORE_URL/);
});

test('reconnect policy is bounded exponential backoff', () => {
  const policy = new ReconnectPolicy({ baseMs: 1000, maxMs: 5000, maxAttempts: 4 });
  assert.equal(policy.delay(1), 1000);
  assert.equal(policy.delay(2), 2000);
  assert.equal(policy.delay(3), 4000);
  assert.equal(policy.delay(4), 5000);
  assert.equal(policy.canRetry(3), true);
  assert.equal(policy.canRetry(4), false);
});

class FakeChild extends EventEmitter {
  constructor() { super(); this.connected = true; this.killed = false; this.messages = []; }
  send(message) { this.messages.push(message); }
  kill() { this.killed = true; this.connected = false; }
}

test('CompanionProcessManager passes token only to worker and sanitizes public status', async () => {
  const child = new FakeChild();
  const published = [];
  const manager = new CompanionProcessManager({
    forkImpl: () => child,
    onStatus: value => published.push(value),
    onRefreshNeeded: async () => 'rotated-access-token-0123456789',
  });
  const initial = manager.start({ coreUrl: 'http://127.0.0.1:8080', sessionToken: 'access-token-0123456789' });
  assert.deepEqual(initial, { state: 'CONNECTING', reason: 'WORKER_STARTED' });
  assert.equal(child.messages[0].sessionToken, 'access-token-0123456789');
  assert.equal(JSON.stringify(initial).includes('access-token'), false);

  child.emit('message', { type: 'status', status: { state: 'ACTIVE', reason: 'HANDSHAKE_ACCEPTED', sessionToken: 'leak' } });
  assert.deepEqual(manager.status, { state: 'ACTIVE', reason: 'HANDSHAKE_ACCEPTED' });
  child.emit('message', { type: 'refresh-needed' });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(child.messages.at(-1).sessionToken, 'rotated-access-token-0123456789');

  manager.stop('KILL_SWITCH');
  assert.equal(child.killed, true);
  assert.deepEqual(manager.status, { state: 'STOPPED', reason: 'KILL_SWITCH' });
  assert.equal(published.some(item => JSON.stringify(item).includes('rotated-access-token')), false);
});

test('sanitizeStatus allowlists fields and drops unexpected data', () => {
  assert.deepEqual(
    sanitizeStatus({ state: 'DEGRADED', reason: 'RECONNECT_SCHEDULED', retryInMs: 1000, token: 'secret' }),
    { state: 'DEGRADED', reason: 'RECONNECT_SCHEDULED', retryInMs: 1000 },
  );
});
