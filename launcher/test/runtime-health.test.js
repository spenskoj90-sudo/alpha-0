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
