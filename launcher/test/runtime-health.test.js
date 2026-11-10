'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { CompanionWorkerRuntime } = require('../companion-worker');
const { BoundedRttStats, CompanionRuntimeHealthTracker } = require('../runtime-health');
const { sanitizeRuntimeHealth } = require('../companion-process');

const CONNECTION_ID = '11111111-1111-4111-8111-111111111111';

function serverHealth(heartbeatMessageId, extra = {}) {
  return {
    health_kind: 'runtime',
    connection_id: CONNECTION_ID,
    heartbeat_message_id: heartbeatMessageId,
    mode: 'ACTIVE',
    reconnect_attempts: 0,
    queue_depth: 0,
    dropped_events: 0,
    kill_switch_active: false,
    peer_authenticated: true,
    ...extra,
  };
}

class FakeWebSocket {
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances = [];

  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = FakeWebSocket.OPEN;
    this.listeners = new Map();
    this.sent = [];
    FakeWebSocket.instances.push(this);
  }

  addEventListener(name, listener) { this.listeners.set(name, listener); }
  send(value) { this.sent.push(value); }
  close(code, reason) { this.readyState = FakeWebSocket.CLOSED; this.emit('close', { code, reason }); }
  emit(name, value = {}) { this.listeners.get(name)?.(value); }
}

test('bounded RTT statistics use a bounded nearest-rank p95 window', () => {
  const stats = new BoundedRttStats({ maxSamples: 3 });
  stats.observe(10);
  stats.observe(30);
  stats.observe(20);
  stats.observe(40);
  assert.deepEqual(stats.snapshot(), {
    count: 3,
    minimumMs: 20,
    maximumMs: 40,
    averageMs: 30,
    p95Ms: 40,
  });
});

test('runtime health requires matching pending heartbeat and ignores injected correlation', () => {
  let now = 1000;
  const tracker = new CompanionRuntimeHealthTracker({ nowMs: () => now, maxPending: 2 });
  const heartbeat = '22222222-2222-4222-8222-222222222222';
  tracker.heartbeatSent(heartbeat);
  now = 1042;

  assert.equal(tracker.accept(serverHealth('33333333-3333-4333-8333-333333333333')), null);
  const accepted = tracker.accept(serverHealth(heartbeat));
  assert.equal(accepted.rttMs, 42);
  assert.equal(accepted.rtt.p95Ms, 42);
  assert.equal(accepted.peerAuthenticated, true);
  assert.equal(tracker.accept(serverHealth(heartbeat)), null);
});

test('worker heartbeat receives correlated Core HEALTH and emits measured runtime health', () => {
  FakeWebSocket.instances.length = 0;
  let now = 5000;
  let heartbeatTick = null;
  const messages = [];
  const runtime = new CompanionWorkerRuntime({
    WebSocketImpl: FakeWebSocket,
    send: message => messages.push(message),
    nowMs: () => now,
    setIntervalImpl: callback => { heartbeatTick = callback; return 1; },
    clearIntervalImpl: () => {},
    setTimeoutImpl: () => 1,
    clearTimeoutImpl: () => {},
  });

  runtime.start({ coreUrl: 'http://127.0.0.1:8000', sessionToken: 'opaque-session-token-0123456789' });
  const socket = FakeWebSocket.instances[0];
  socket.emit('open');
  socket.emit('message', { data: JSON.stringify({ accepted: true, reason_code: 'HANDSHAKE_ACCEPTED', mode: 'ACTIVE' }) });
  assert.equal(typeof heartbeatTick, 'function');

  heartbeatTick();
  const heartbeat = JSON.parse(socket.sent.at(-1));
  assert.equal(heartbeat.message_type, 'HEARTBEAT');
  now = 5037;
  socket.emit('message', {
    data: JSON.stringify({
      message_id: '44444444-4444-4444-8444-444444444444',
      sequence: heartbeat.sequence,
      message_type: 'HEALTH',
      latency_class: 'RESPONSIVE',
      payload: serverHealth(heartbeat.message_id),
    }),
  });

  const runtimeMessage = messages.find(message => message.type === 'runtime-health');
  assert.ok(runtimeMessage);
  assert.equal(runtimeMessage.health.rttMs, 37);
  assert.equal(runtimeMessage.health.rtt.count, 1);
  assert.equal(runtimeMessage.health.connectionId, CONNECTION_ID);
  assert.equal(JSON.stringify(runtimeMessage).includes('opaque-session-token'), false);
});

test('worker discards stale websocket callbacks across rotation, Stop, and fresh start', () => {
  FakeWebSocket.instances.length = 0;
  const outputs = [];
  const runtime = new CompanionWorkerRuntime({
    WebSocketImpl: FakeWebSocket,
    send: value => outputs.push(value),
    setTimeoutImpl: () => 1,
    clearTimeoutImpl: () => {},
    setIntervalImpl: () => 1,
    clearIntervalImpl: () => {},
  });
  const coreUrl = 'http://127.0.0.1:8000';
  runtime.start({ coreUrl, sessionToken: 'opaque-session-token-0123456789' });
  const old = FakeWebSocket.instances[0];
  // Session rotation races a delayed close from the previous connection.
  old.readyState = FakeWebSocket.CLOSED;
  runtime.updateSession('rotated-session-token-0123456789');
  const current = FakeWebSocket.instances[1];
  assert.equal(runtime.socket, current);
  old.emit('message', { data: 'invalid stale frame' });
  old.emit('error');
  old.emit('close', { reason: 'COMPANION_ENTITLEMENT_REVOKED' });
  const oldSends = old.sent.length;
  old.emit('open');
  assert.equal(old.sent.length, oldSends);
  assert.equal(runtime.socket, current);
  assert.equal(runtime.running, true);

  current.emit('open');
  current.emit('message', { data: JSON.stringify({ accepted: true, mode: 'ACTIVE' }) });
  assert.equal(runtime.state, 'ACTIVE');
  assert.equal(outputs.filter(item => item.type === 'handshake-evidence').length, 1);
  assert.throws(() => runtime.start({ coreUrl, sessionToken: 'third-session-token-0123456789' }),
    /COMPANION_ALREADY_RUNNING/);
  assert.equal(FakeWebSocket.instances.length, 2);

  runtime.stop('KILL_SWITCH');
  current.emit('message', { data: 'invalid after stop' });
  current.emit('error');
  current.emit('open');
  assert.equal(runtime.state, 'STOPPED');
  assert.equal(runtime.reason, 'KILL_SWITCH');
  runtime.start({ coreUrl, sessionToken: 'fresh-session-token-0123456789' });
  assert.equal(FakeWebSocket.instances.length, 3);
  runtime.stop('TEST_DONE');
});

test('worker replaces an ACTIVE credential, fences queued callbacks, and clears credentials on Stop', () => {
  FakeWebSocket.instances.length = 0;
  const outputs = [];
  const reconnectCallbacks = [];
  const heartbeatCallbacks = [];
  const runtime = new CompanionWorkerRuntime({
    WebSocketImpl: FakeWebSocket,
    send: value => outputs.push(value),
    setTimeoutImpl: callback => { reconnectCallbacks.push(callback); return reconnectCallbacks.length; },
    clearTimeoutImpl: () => {},
    setIntervalImpl: callback => { heartbeatCallbacks.push(callback); return heartbeatCallbacks.length; },
    clearIntervalImpl: () => {},
  });
  const coreUrl = 'http://127.0.0.1:8000';
  const oldToken = 'original-session-token-0123456789';
  const rotated = 'rotated-session-token-0123456789';
  runtime.start({ coreUrl, sessionToken: oldToken });
  const first = FakeWebSocket.instances[0];
  first.emit('open');
  first.emit('message', { data: JSON.stringify({ accepted: true, mode: 'ACTIVE' }) });
  assert.equal(runtime.state, 'ACTIVE');
  assert.equal(runtime.sendWowObservation({ event_id: 'before-rotation' }), true);
  const heartbeatFromFirst = heartbeatCallbacks[0];

  runtime.updateSession(rotated);
  const second = FakeWebSocket.instances[1];
  assert.equal(first.readyState, FakeWebSocket.CLOSED);
  assert.equal(runtime.state, 'CONNECTING');
  assert.equal(runtime.handshaken, false);
  assert.equal(runtime.sendWowObservation({ event_id: 'during-rotation' }), false);
  assert.equal(second.protocols[1].includes(Buffer.from(oldToken).toString('base64url')), false);
  heartbeatFromFirst();
  assert.equal(second.sent.length, 0);

  first.emit('message', { data: 'stale invalid JSON' });
  first.emit('close', { reason: 'COMPANION_ENTITLEMENT_REVOKED' });
  second.emit('open');
  second.emit('message', { data: JSON.stringify({ accepted: true, mode: 'ACTIVE' }) });
  assert.equal(runtime.state, 'ACTIVE');
  heartbeatFromFirst();
  assert.equal(second.sent.length, 1);
  assert.equal(runtime.sendWowObservation({ event_id: 'after-rotation' }), true);
  runtime.updateSession(rotated);
  assert.equal(FakeWebSocket.instances.length, 2);

  second.readyState = FakeWebSocket.CLOSED;
  second.emit('close', { reason: 'TEMPORARY_NETWORK_LOSS' });
  assert.equal(reconnectCallbacks.length, 1);
  runtime.updateSession('new-session-token-0123456789');
  const third = FakeWebSocket.instances[2];
  reconnectCallbacks[0](); // Even a cancelled callback already queued cannot create a fourth connection.
  assert.equal(runtime.socket, third);
  assert.equal(FakeWebSocket.instances.length, 3);
  third.emit('open');
  third.emit('message', { data: JSON.stringify({ accepted: true, mode: 'ACTIVE' }) });
  runtime.stop('KILL_SWITCH');
  assert.equal(runtime.token, null);
  assert.equal(runtime.coreUrl, null);
  assert.equal(runtime.handshaken, false);
  assert.deepEqual(outputs.at(-1).status, { state: 'STOPPED', reason: 'KILL_SWITCH' });
});

test('worker terminal entitlement rejection scrubs token and never reconnects implicitly', () => {
  FakeWebSocket.instances.length = 0;
  const runtime = new CompanionWorkerRuntime({
    WebSocketImpl: FakeWebSocket,
    send: () => {},
    setTimeoutImpl: () => 1,
    clearTimeoutImpl: () => {},
    setIntervalImpl: () => 1,
    clearIntervalImpl: () => {},
  });
  runtime.start({ coreUrl: 'http://localhost:8000', sessionToken: 'original-session-token-0123456789' });
  FakeWebSocket.instances[0].readyState = FakeWebSocket.CLOSED;
  FakeWebSocket.instances[0].emit('close', { reason: 'COMPANION_ENTITLEMENT_REVOKED' });
  assert.equal(runtime.state, 'STOPPED');
  assert.equal(runtime.running, false);
  assert.equal(runtime.token, null);
  assert.equal(runtime.coreUrl, null);
  runtime.updateSession('new-session-token-0123456789');
  assert.equal(FakeWebSocket.instances.length, 1);
});

test('parent runtime-health sanitizer allowlists fields and drops secrets', () => {
  const safe = sanitizeRuntimeHealth({
    healthKind: 'runtime',
    connectionId: CONNECTION_ID,
    heartbeatMessageId: '55555555-5555-4555-8555-555555555555',
    mode: 'ACTIVE',
    reconnectAttempts: 0,
    queueDepth: 0,
    droppedEvents: 0,
    killSwitchActive: false,
    peerAuthenticated: true,
    rttMs: 12,
    rtt: { count: 1, minimumMs: 12, maximumMs: 12, averageMs: 12, p95Ms: 12 },
    sessionToken: 'must-not-cross-parent-boundary',
  });
  assert.equal(safe.rtt.p95Ms, 12);
  assert.equal(Object.hasOwn(safe, 'sessionToken'), false);
  assert.equal(sanitizeRuntimeHealth({ ...safe, connectionId: 'not-a-uuid' }), null);
});
