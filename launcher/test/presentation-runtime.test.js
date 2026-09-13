'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { CompanionWorkerRuntime } = require('../companion-worker');
const { PresentationStore, sanitizePresentation } = require('../presentation-runtime');

function presentation(id = '11111111-1111-4111-8111-111111111111', overrides = {}) {
  return {
    presentation_id: id,
    correlation_id: '22222222-2222-4222-8222-222222222222',
    channel: 'OVERLAY',
    kind: 'RECOMMENDATION',
    text: 'Stay defensive while the passive signal is incomplete.',
    confidence: 0.72,
    provenance: ['sentinel-core'],
    action_capable: false,
    ...overrides,
  };
}

test('presentation sanitizer allowlists non-actionable overlay content', () => {
  const sanitized = sanitizePresentation({ ...presentation(), action: 'attack-target', secret: 'drop-me' });
  assert.equal(sanitized.channel, 'OVERLAY');
  assert.equal(sanitized.action_capable, false);
  assert.equal(sanitized.text.includes('attack-target'), false);
  assert.equal(Object.prototype.hasOwnProperty.call(sanitized, 'action'), false);
  assert.equal(Object.prototype.hasOwnProperty.call(sanitized, 'secret'), false);
  assert.throws(() => sanitizePresentation(presentation(undefined, { action_capable: true })), /PRESENTATION_ACTION_CAPABILITY_FORBIDDEN/);
  assert.throws(() => sanitizePresentation(presentation(undefined, { channel: 'VOICE' })), /PRESENTATION_CHANNEL_UNSUPPORTED/);
  assert.throws(() => sanitizePresentation(presentation(undefined, { text: 'x'.repeat(2001) })), /PRESENTATION_TEXT_INVALID/);
});

test('presentation store is bounded, deduplicated and expires items with injected timers', () => {
  const scheduled = [];
  const cleared = [];
  let now = 1000;
  const snapshots = [];
  const store = new PresentationStore({
    maxItems: 2,
    now: () => now,
    setTimeoutImpl: (callback, delay) => {
      const timer = { callback, delay, unref() {} };
      scheduled.push(timer);
      return timer;
    },
    clearTimeoutImpl: timer => cleared.push(timer),
    onChange: snapshot => snapshots.push(snapshot),
  });

  const a = presentation('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', { kind: 'STATUS' });
  const b = presentation('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
  const c = presentation('cccccccc-cccc-4ccc-8ccc-cccccccccccc', { kind: 'ALERT' });
  assert.equal(store.add(a), true);
  assert.equal(store.add(a), false);
  now += 10;
  assert.equal(store.add(b), true);
  now += 10;
  assert.equal(store.add(c), true);
  assert.equal(store.depth, 2);
  assert.deepEqual(store.snapshot().map(item => item.presentation_id), [b.presentation_id, c.presentation_id]);
  assert.equal(cleared.length, 1);
  assert.equal(scheduled[0].delay, 8000);
  assert.equal(scheduled[1].delay, 20000);
  assert.equal(scheduled[2].delay, 30000);

  scheduled[1].callback();
  assert.equal(store.depth, 1);
  assert.equal(store.snapshot()[0].presentation_id, c.presentation_id);
  store.clear();
  assert.equal(store.depth, 0);
  assert.equal(snapshots.at(-1).length, 0);
});

class FakeWebSocket {
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static last = null;

  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = FakeWebSocket.OPEN;
    this.listeners = new Map();
    this.sent = [];
    this.closed = null;
    FakeWebSocket.last = this;
  }

  addEventListener(type, callback) {
    const list = this.listeners.get(type) || [];
    list.push(callback);
    this.listeners.set(type, list);
  }

  emit(type, event = {}) {
    for (const callback of this.listeners.get(type) || []) callback(event);
  }

  send(value) { this.sent.push(value); }

  close(code, reason) {
    this.closed = { code, reason };
    this.readyState = FakeWebSocket.CLOSED;
  }
}

test('Companion worker forwards valid presentations and fail-closes invalid presentation payloads', () => {
  const parentMessages = [];
  const runtime = new CompanionWorkerRuntime({
    WebSocketImpl: FakeWebSocket,
    send: message => parentMessages.push(message),
    setIntervalImpl: () => 1,
    clearIntervalImpl: () => {},
  });
  runtime.start({ coreUrl: 'http://127.0.0.1:8080', sessionToken: 'opaque-session-token-0123456789' });
  const socket = FakeWebSocket.last;
  socket.emit('open');
  socket.emit('message', { data: JSON.stringify({ accepted: true, mode: 'ACTIVE' }) });
  socket.emit('message', { data: JSON.stringify({ message_type: 'PRESENTATION', payload: presentation() }) });
  const forwarded = parentMessages.find(message => message.type === 'presentation');
  assert.ok(forwarded);
  assert.deepEqual(forwarded.presentation, sanitizePresentation(presentation()));

  socket.emit('message', {
    data: JSON.stringify({
      message_type: 'PRESENTATION',
      payload: presentation(undefined, { action_capable: true }),
    }),
  });
  assert.equal(runtime.state, 'STOPPED');
  assert.equal(runtime.reason, 'PRESENTATION_ACTION_CAPABILITY_FORBIDDEN');
  assert.deepEqual(socket.closed, { code: 1000, reason: 'PRESENTATION_ACTION_CAPABILITY_FORBIDDEN' });
});
