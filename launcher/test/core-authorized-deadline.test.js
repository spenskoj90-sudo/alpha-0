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

test('Core rejects oversized declared feature response before parsing body', async () => {
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    return Promise.resolve(new Response('{"features":[]}', {
      status: 200, headers: { 'content-length': String(4 * 1024 * 1024) },
    }));
  });
  await login(manager);
  await assert.rejects(manager.featureStatus(), /CORE_SIZE_INVALID/);
});

test('Core rejects a streamed oversized body without a declared content length', async () => {
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    return Promise.resolve(new Response(new Uint8Array(3 * 1024 * 1024 + 1), { status: 200 }));
  }, 2000);
  await login(manager);
  await assert.rejects(manager.voiceStatus(), /CORE_SIZE_INVALID/);
});

test('Core handles malformed streamed JSON as an explicit error', async () => {
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    return Promise.resolve(new Response('not valid json', { status: 200 }));
  });
  await login(manager);
  await assert.rejects(manager.featureStatus(), /CORE_RESPONSE_INVALID/);
});

test('Core parses a normal streamed JSON response', async () => {
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    return Promise.resolve(Response.json({ features: ['companion'] }));
  });
  await login(manager);
  assert.deepEqual(await manager.featureStatus(), { features: ['companion'] });
});

test('Core releases unauthorized streamed body before one-use refresh retry', async () => {
  let cancelled = false;
  let lookups = 0;
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    if (url.endsWith('/v1/sessions/refresh')) return Promise.resolve(reply(200, {
      session_token: 'refreshed-access', refresh_token: 'refreshed-refresh',
    }));
    if (url.endsWith('/v1/billing/features')) {
      if (++lookups === 1) return Promise.resolve({
        status: 401, ok: false, body: { cancel: () => {
          cancelled = true; return Promise.resolve();
        } }, json: async () => ({ code: 'EXPIRED' }),
      });
      return Promise.resolve(reply(200, { features: ['companion'] }));
    }
    throw new Error('UNEXPECTED_ROUTE');
  }, 200);
  await login(manager);
  assert.deepEqual(await manager.featureStatus(), { features: ['companion'] });
  assert.equal(lookups, 2);
  assert.equal(cancelled, true);
  assert.equal(manager.accessToken, 'refreshed-access');
});

test('email login has finite deadline when authentication transport never resolves', async () => {
  let signal;
  const manager = create((_url, init) => {
    signal = init.signal;
    return new Promise(() => {});
  }, 30);
  await assert.rejects(login(manager), /CORE_REQUEST_TIMEOUT/);
  assert.equal(signal.aborted, true);
  assert.equal(manager.status, null);
});

test('MFA completion has a deadline without consuming the pending challenge', async () => {
  let completionSignal;
  const manager = create((url, init) => {
    if (url.endsWith('/v1/auth/login')) {
      return Promise.resolve(reply(200, {
        mfa_required: true, challenge_token: 'c'.repeat(48),
      }));
    }
    completionSignal = init.signal;
    return new Promise(() => {});
  }, 30);
  await login(manager);
  assert.equal(manager.mfaStatus.required, true);
  await assert.rejects(manager.completeMfa('123456'), /CORE_REQUEST_TIMEOUT/);
  assert.equal(completionSignal.aborted, true);
  assert.equal(manager.mfaStatus.required, true);
  assert.equal(manager.status, null);
});

test('logout revokes pending MFA even when the old provider ignores abort', async () => {
  let completionSignal;
  const manager = create((url, init) => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, {
      mfa_required: true, challenge_token: 'm'.repeat(48),
    }));
    completionSignal = init.signal;
    return new Promise(() => {});
  }, 200);
  await login(manager);
  const pending = manager.completeMfa('123456');
  manager.clear();
  await assert.rejects(pending, /SESSION_CHANGED/);
  assert.equal(completionSignal.aborted, true);
  assert.equal(manager.mfaStatus, null);
});

test('login also rejects malformed or oversized real streamed Core responses', async () => {
  let count = 0;
  const manager = create(() => {
    ++count;
    if (count === 1) return Promise.resolve(new Response('not json', { status: 200 }));
    return Promise.resolve(new Response('{"hello":true}', {
      status: 200, headers: { 'content-length': String(4 * 1024 * 1024) },
    }));
  });
  await assert.rejects(login(manager), /CORE_RESPONSE_INVALID/);
  await assert.rejects(login(manager), /CORE_SIZE_INVALID/);
  assert.equal(manager.status, null);
});

test('Core accepts a finite empty stream chunk before a valid JSON response', async () => {
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    let reads = 0;
    return Promise.resolve(new Response(new ReadableStream({
      pull(controller) {
        if (reads++ === 0) controller.enqueue(new Uint8Array());
        else {
          controller.enqueue(new TextEncoder().encode('{"features":["companion"]}'));
          controller.close();
        }
      },
    }), { status: 200 }));
  });
  await login(manager);
  assert.deepEqual(await manager.featureStatus(), { features: ['companion'] });
});

test('Core rejects a stream with repeated zero-progress chunks without waiting on a timer', async () => {
  let cancelled = false;
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    let emptyChunks = 0;
    return Promise.resolve(new Response(new ReadableStream({
      pull(controller) {
        if (++emptyChunks <= 33) controller.enqueue(new Uint8Array());
        else {
          controller.enqueue(new TextEncoder().encode('{"features":["companion"]}'));
          controller.close();
        }
      },
      cancel() { cancelled = true; },
    }), { status: 200 }));
  }, 200);
  await login(manager);
  await assert.rejects(manager.featureStatus(), /CORE_RESPONSE_INVALID/);
  assert.equal(cancelled, true);
});

test('Core caps tiny streamed reads even when total bytes remain below the size limit', async () => {
  const manager = create(url => {
    if (url.endsWith('/v1/auth/login')) return Promise.resolve(reply(200, credentials));
    let emitted = 0;
    return Promise.resolve(new Response(new ReadableStream({
      pull(controller) {
        if (emitted++ < 32769) controller.enqueue(new Uint8Array([32]));
        else controller.close();
      },
    }), { status: 200 }));
  }, 2000);
  await login(manager);
  await assert.rejects(manager.featureStatus(), /CORE_RESPONSE_INVALID/);
});
