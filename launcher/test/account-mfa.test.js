'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { CoreSessionManager } = require('../core-session');

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test('MFA challenge stays in main-process session manager and becomes a session only after verification', async () => {
  const calls = [];
  const rawChallenge = 'mfa-secret-challenge-token-abcdefghijklmnopqrstuvwxyz0123456789';
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, init });
      if (url.endsWith('/v1/auth/login')) {
        return response(200, {
          mfa_required: true,
          challenge_token: rawChallenge,
          expires_at: '2030-01-01T00:05:00Z',
        });
      }
      if (url.endsWith('/v1/auth/mfa/complete')) {
        return response(200, {
          session_token: 'access-token-after-mfa',
          refresh_token: 'refresh-token-after-mfa',
          expires_at: '2030-01-01T01:00:00Z',
          scopes: ['game:read'],
        });
      }
      throw new Error('unexpected request: ' + url);
    },
  });

  const first = await manager.login({
    coreUrl: 'http://127.0.0.1:8080',
    email: 'mfa@example.com',
    password: 'correct-password',
  });
  assert.equal(first, null);
  assert.deepEqual(manager.mfaStatus, { required: true, expiresAt: '2030-01-01T00:05:00Z' });
  assert.equal(JSON.stringify(manager.mfaStatus).includes(rawChallenge), false);
  assert.equal(manager.accessToken, null);

  const completed = await manager.completeMfa('123456');
  assert.deepEqual(completed, {
    authenticated: true,
    expiresAt: '2030-01-01T01:00:00Z',
    scopes: ['game:read'],
  });
  assert.equal(manager.mfaStatus, null);
  assert.equal(manager.accessToken, 'access-token-after-mfa');

  const body = JSON.parse(calls[1].init.body);
  assert.equal(body.challenge_token, rawChallenge);
  assert.equal(body.code, '123456');
  await assert.rejects(manager.completeMfa('123456'), /MFA_CHALLENGE_REQUIRED/);
});

test('invalid MFA response never creates a launcher session', async () => {
  const manager = new CoreSessionManager({
    fetchImpl: async url => {
      if (url.endsWith('/v1/auth/login')) {
        return response(200, { mfa_required: true, challenge_token: 'x'.repeat(48) });
      }
      return response(200, { unexpected: true });
    },
  });

  await manager.login({
    coreUrl: 'http://localhost:8080',
    email: 'mfa@example.com',
    password: 'correct-password',
  });
  await assert.rejects(manager.completeMfa('123456'), /INVALID_SESSION_RESPONSE/);
  assert.equal(manager.status, null);
  assert.equal(manager.accessToken, null);
});

function delayedReply() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

test('logout invalidates an in-flight login even if its successful reply arrives later', async () => {
  const deferred = delayedReply();
  const manager = new CoreSessionManager({ fetchImpl: () => deferred.promise });
  const pending = manager.login({
    coreUrl: 'http://127.0.0.1:8080', email: 'old@example.test', password: 'secret',
  });
  manager.clear();
  deferred.resolve(response(200, {
    session_token: 'stale-access-after-logout', refresh_token: 'stale-refresh-after-logout',
  }));
  await assert.rejects(pending, /SESSION_CHANGED/);
  assert.equal(manager.status, null);
  assert.equal(manager.accessToken, null);
  assert.equal(manager.refreshToken, null);
});

test('late older login cannot replace the newer account after responses arrive out of order', async () => {
  const requests = [];
  const manager = new CoreSessionManager({
    fetchImpl: (_url, init) => {
      const deferred = delayedReply();
      requests.push({ email: JSON.parse(init.body).email, deferred });
      return deferred.promise;
    },
  });
  const first = manager.login({
    coreUrl: 'http://127.0.0.1:8080', email: 'first@example.test', password: 'one',
  });
  const second = manager.login({
    coreUrl: 'http://127.0.0.1:8080', email: 'second@example.test', password: 'two',
  });
  assert.equal(requests.length, 2);
  requests[1].deferred.resolve(response(200, {
    session_token: 'newer-access', refresh_token: 'newer-refresh',
  }));
  await second;
  requests[0].deferred.resolve(response(200, {
    session_token: 'older-access', refresh_token: 'older-refresh',
  }));
  await assert.rejects(first, /SESSION_CHANGED/);
  assert.equal(manager.accessToken, 'newer-access');
  assert.equal(manager.refreshToken, 'newer-refresh');
});

test('late MFA completion cannot restore a logged-out session', async () => {
  const deferred = delayedReply();
  const manager = new CoreSessionManager({
    fetchImpl: url => url.endsWith('/v1/auth/login')
      ? response(200, { mfa_required: true, challenge_token: 'x'.repeat(48) })
      : deferred.promise,
  });
  await manager.login({
    coreUrl: 'http://127.0.0.1:8080', email: 'mfa@example.test', password: 'secret',
  });
  const pending = manager.completeMfa('123456');
  manager.clear();
  deferred.resolve(response(200, {
    session_token: 'stale-mfa-access', refresh_token: 'stale-mfa-refresh',
  }));
  await assert.rejects(pending, /SESSION_CHANGED/);
  assert.equal(manager.mfaStatus, null);
  assert.equal(manager.accessToken, null);
});

test('new login revokes old MFA challenge and rejects its delayed completion', async () => {
  const deferred = delayedReply();
  let logins = 0;
  const manager = new CoreSessionManager({
    fetchImpl: url => {
      if (url.endsWith('/v1/auth/mfa/complete')) return deferred.promise;
      logins += 1;
      if (logins === 1) return response(200, {
        mfa_required: true, challenge_token: 'y'.repeat(48),
      });
      return response(200, { session_token: 'fresh-access', refresh_token: 'fresh-refresh' });
    },
  });
  await manager.login({
    coreUrl: 'http://127.0.0.1:8080', email: 'first@example.test', password: 'one',
  });
  const oldMfa = manager.completeMfa('123456');
  await manager.login({
    coreUrl: 'http://127.0.0.1:8080', email: 'next@example.test', password: 'two',
  });
  deferred.resolve(response(200, {
    session_token: 'stale-mfa-access', refresh_token: 'stale-mfa-refresh',
  }));
  await assert.rejects(oldMfa, /SESSION_CHANGED/);
  assert.equal(manager.accessToken, 'fresh-access');
  assert.equal(manager.mfaStatus, null);
});
