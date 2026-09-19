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
