'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { CoreSessionManager } = require('../core-session');

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function header(init, name) {
  const entries = Object.entries(init.headers || {});
  return entries.find(([key]) => key.toLowerCase() === name.toLowerCase())?.[1] || null;
}

test('CoreSessionManager attaches bounded UUID request ids to login and refresh', async () => {
  const calls = [];
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, init });
      return response(200, {
        session_token: `access-${calls.length}-0123456789`,
        refresh_token: `refresh-${calls.length}-0123456789`,
        scopes: [],
      });
    },
  });
  await manager.login({ coreUrl: 'http://127.0.0.1:8080', email: 'user@example.com', password: 'secret' });
  await manager.refresh();
  assert.match(header(calls[0].init, 'x-request-id'), /^[0-9a-f-]{36}$/i);
  assert.match(header(calls[1].init, 'x-request-id'), /^[0-9a-f-]{36}$/i);
  assert.notEqual(header(calls[0].init, 'x-request-id'), header(calls[1].init, 'x-request-id'));
});

test('authorized retry and token refresh preserve one logical correlation id', async () => {
  const calls = [];
  let featureAttempts = 0;
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, init });
      if (url.endsWith('/v1/auth/login')) {
        return response(200, { session_token: 'access-old-0123456789', refresh_token: 'refresh-old-0123456789', scopes: [] });
      }
      if (url.endsWith('/v1/billing/features')) {
        featureAttempts += 1;
        return featureAttempts === 1 ? response(401, { detail: 'INVALID_SESSION' }) : response(200, { features: ['companion'] });
      }
      if (url.endsWith('/v1/sessions/refresh')) {
        return response(200, { session_token: 'access-new-0123456789', refresh_token: 'refresh-new-0123456789', scopes: [] });
      }
      throw new Error(`unexpected url ${url}`);
    },
  });

  await manager.login({ coreUrl: 'http://127.0.0.1:8080', email: 'user@example.com', password: 'secret' });
  await manager.featureStatus();
  const logical = calls.slice(1).map(call => header(call.init, 'x-request-id'));
  assert.equal(logical.length, 3);
  assert.ok(logical.every(value => value === logical[0]));
  assert.match(logical[0], /^[0-9a-f-]{36}$/i);
});
