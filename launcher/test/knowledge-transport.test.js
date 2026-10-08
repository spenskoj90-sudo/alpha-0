'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { CoreSessionManager } = require('../core-session');

const profile = Object.freeze({
  game: 'fixture', platform: 'windows', patch: '1', environment: 'offline-fixture', profile: 'tank',
});

function loginResponse(token = 'access-old') {
  return new Response(JSON.stringify({
    session_token: token, refresh_token: 'refresh-token', scopes: ['game:read'],
  }), { status: 200, headers: { 'content-type': 'application/json' } });
}

function header(init, name) {
  return Object.entries(init.headers || {})
    .find(([key]) => key.toLowerCase() === name.toLowerCase())?.[1] || null;
}

async function login(manager) {
  await manager.login({
    coreUrl: 'https://core.example.test', email: 'fixture@example.test', password: 'secret',
  });
}

test('knowledge deadline includes a stalled refresh body and is shared across every request', async () => {
  const signals = [];
  let cancelled = false;
  const manager = new CoreSessionManager({ knowledgeTimeoutMs: 25,
    fetchImpl: async (url, init) => {
      if (url.endsWith('/v1/auth/login')) return loginResponse();
      signals.push(init.signal);
      if (url.endsWith('/v1/sessions/refresh')) {
        assert.equal(init.redirect, 'error');
        return new Response(new ReadableStream({ cancel() { cancelled = true; } }));
      }
      return new Response('{}', { status: 401 });
    },
  });
  await login(manager);
  await assert.rejects(manager.knowledgeManifest(profile), /KNOWLEDGE_TIMEOUT/);
  assert.equal(signals.length, 2);
  assert.ok(signals[0] instanceof AbortSignal);
  assert.equal(signals[0], signals[1]);
  assert.equal(cancelled, true);
});

test('logout during refresh cannot restore the retired session', async () => {
  let finish;
  let refreshing;
  const reached = new Promise(resolve => { refreshing = resolve; });
  const manager = new CoreSessionManager({ fetchImpl: async url => {
    if (url.endsWith('/v1/auth/login')) return loginResponse();
    if (url.endsWith('/v1/sessions/refresh')) {
      refreshing();
      return new Promise(resolve => { finish = resolve; });
    }
    return new Response('{}', { status: 401 });
  } });
  await login(manager);
  const pending = manager.knowledgeManifest(profile);
  await reached;
  manager.clear();
  finish(loginResponse('retired-access'));
  await assert.rejects(pending, /KNOWLEDGE_SESSION_CHANGED/);
  assert.equal(manager.status, null);
});

test('Stop cancels a stalled stream immediately while preserving account authority', async () => {
  let reading;
  const reached = new Promise(resolve => { reading = resolve; });
  let cancelled = false;
  const manager = new CoreSessionManager({ fetchImpl: async url => {
    if (url.endsWith('/v1/auth/login')) return loginResponse();
    return new Response(new ReadableStream({ pull() { reading(); }, cancel() { cancelled = true; } }));
  } });
  await login(manager);
  const pending = manager.knowledgePack(profile, 'a'.repeat(64));
  await reached;
  manager.cancelKnowledge();
  await assert.rejects(pending, /KNOWLEDGE_SESSION_CHANGED/);
  assert.equal(cancelled, true);
  assert.equal(manager.accessToken, 'access-old');
});

test('knowledge reads require auth and bind origin, exact query, token and redirect policy', async () => {
  const requests = [];
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      if (url.endsWith('/v1/auth/login')) return loginResponse();
      requests.push({ url, init });
      return new Response(JSON.stringify({ status: 'unavailable' }), {
        status: 200, headers: { 'content-type': 'application/json' },
      });
    },
  });
  await assert.rejects(manager.knowledgeManifest(profile), /AUTHENTICATION_REQUIRED/);
  await login(manager);
  assert.equal((await manager.knowledgeManifest(profile, 'a'.repeat(64))).status, 'unavailable');

  const request = requests[0];
  const url = new URL(request.url);
  assert.equal(url.origin, 'https://core.example.test');
  assert.equal(url.pathname, '/v1/knowledge/manifest');
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    game: 'fixture', platform: 'windows', patch: '1',
    environment: 'offline-fixture', profile: 'tank', known_digest: 'a'.repeat(64),
  });
  assert.equal(header(request.init, 'authorization'), 'Bearer access-old');
  assert.match(header(request.init, 'x-request-id'), /^[0-9a-f-]{36}$/i);
  assert.equal(request.init.redirect, 'error');
  assert.equal(request.init.cache, 'no-store');
  assert.ok(request.init.signal instanceof AbortSignal);
});

test('pack and delta paths accept only canonical digests and delta binds its base', async () => {
  const requests = [];
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      if (url.endsWith('/v1/auth/login')) return loginResponse();
      requests.push({ url, init });
      if (url.includes('/deltas/')) return new Response(JSON.stringify({ schema_version: 1 }));
      return new Response(new Uint8Array([123, 125]));
    },
  });
  await login(manager);
  await assert.rejects(manager.knowledgePack(profile, '../arbitrary'), /KNOWLEDGE_DIGEST_INVALID/);
  await assert.rejects(manager.knowledgeDelta(profile, 'a'.repeat(64), 'not-a-digest'), /KNOWLEDGE_DIGEST_INVALID/);
  assert.deepEqual(await manager.knowledgePack(profile, 'a'.repeat(64)), Buffer.from('{}'));
  assert.deepEqual(await manager.knowledgeDelta(profile, 'b'.repeat(64), 'a'.repeat(64)), { schema_version: 1 });
  const delta = new URL(requests[1].url);
  assert.equal(delta.pathname, `/v1/knowledge/deltas/${'b'.repeat(64)}`);
  assert.equal(delta.searchParams.get('base_digest'), 'a'.repeat(64));
});

test('streamed bodies are rejected as soon as their configured bound is crossed', async () => {
  const oversizedPack = new Uint8Array(262145);
  const oversizedJson = JSON.stringify({ insert_b64: 'a'.repeat(354000) });
  let mode = 'pack';
  const manager = new CoreSessionManager({
    fetchImpl: async url => {
      if (url.endsWith('/v1/auth/login')) return loginResponse();
      return mode === 'pack' ? new Response(oversizedPack) : new Response(oversizedJson);
    },
  });
  await login(manager);
  await assert.rejects(manager.knowledgePack(profile, 'a'.repeat(64)), /KNOWLEDGE_SIZE_INVALID/);
  mode = 'json';
  await assert.rejects(
    manager.knowledgeDelta(profile, 'b'.repeat(64), 'a'.repeat(64)),
    /KNOWLEDGE_SIZE_INVALID/,
  );
});

test('knowledge 401 refreshes once with one correlation id and the rotated bearer', async () => {
  const calls = [];
  let manifestAttempts = 0;
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, init });
      if (url.endsWith('/v1/auth/login')) return loginResponse();
      if (url.endsWith('/v1/sessions/refresh')) return loginResponse('access-new');
      manifestAttempts += 1;
      if (manifestAttempts === 1) return new Response('{}', { status: 401 });
      return new Response(JSON.stringify({ status: 'unavailable' }), { status: 200 });
    },
  });
  await login(manager);
  assert.equal((await manager.knowledgeManifest(profile)).status, 'unavailable');
  const logical = calls.slice(1);
  assert.equal(logical.length, 3);
  assert.ok(logical.every(call => header(call.init, 'x-request-id') === header(logical[0].init, 'x-request-id')));
  assert.equal(header(logical[0].init, 'authorization'), 'Bearer access-old');
  assert.equal(header(logical[2].init, 'authorization'), 'Bearer access-new');
});

test('failed refresh after a knowledge 401 clears the rejected session', async () => {
  const manager = new CoreSessionManager({
    fetchImpl: async url => {
      if (url.endsWith('/v1/auth/login')) return loginResponse();
      if (url.endsWith('/v1/sessions/refresh')) return new Response('{}', { status: 200 });
      return new Response('{}', { status: 401 });
    },
  });
  await login(manager);
  await assert.rejects(manager.knowledgeManifest(profile), /AUTHENTICATION_REQUIRED/);
  assert.equal(manager.status, null);
  assert.equal(manager.accessToken, null);
});

test('access denial is classified and a cleared session rejects an in-flight response', async () => {
  let mode = 'denied';
  let finish;
  const manager = new CoreSessionManager({
    fetchImpl: async url => {
      if (url.endsWith('/v1/auth/login')) return loginResponse();
      if (mode === 'denied') return new Response('{}', { status: 403 });
      return new Promise(resolve => { finish = resolve; });
    },
  });
  await login(manager);
  await assert.rejects(manager.knowledgeManifest(profile), /KNOWLEDGE_ACCESS_DENIED/);
  mode = 'pending';
  const pending = manager.knowledgeManifest(profile);
  manager.clear();
  finish(new Response(JSON.stringify({ status: 'unavailable' }), { status: 200 }));
  await assert.rejects(pending, /KNOWLEDGE_SESSION_CHANGED/);
});
