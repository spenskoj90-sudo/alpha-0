'use strict';

const { performance } = require('node:perf_hooks');

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MODES = new Set(['ACTIVE', 'DEGRADED', 'STOPPED']);

function boundedInteger(value, max = 1_000_000) {
  return Number.isSafeInteger(value) && value >= 0 && value <= max ? value : null;
}

function sanitizeServerRuntimeHealth(payload) {
  if (!payload || typeof payload !== 'object' || payload.health_kind !== 'runtime') return null;
  const connectionId = typeof payload.connection_id === 'string' && UUID_RE.test(payload.connection_id) ? payload.connection_id : null;
  const heartbeatMessageId = typeof payload.heartbeat_message_id === 'string' && UUID_RE.test(payload.heartbeat_message_id) ? payload.heartbeat_message_id : null;
  const mode = typeof payload.mode === 'string' && MODES.has(payload.mode) ? payload.mode : null;
  const reconnectAttempts = boundedInteger(payload.reconnect_attempts, 10_000);
  const queueDepth = boundedInteger(payload.queue_depth, 4096);
  const droppedEvents = boundedInteger(payload.dropped_events, 1_000_000);
  if (!connectionId || !heartbeatMessageId || !mode || reconnectAttempts === null || queueDepth === null || droppedEvents === null) return null;
  if (typeof payload.kill_switch_active !== 'boolean' || typeof payload.peer_authenticated !== 'boolean') return null;
  return {
    healthKind: 'runtime',
    connectionId,
    heartbeatMessageId,
    mode,
    reconnectAttempts,
    queueDepth,
    droppedEvents,
    killSwitchActive: payload.kill_switch_active,
    peerAuthenticated: payload.peer_authenticated,
  };
}

class BoundedRttStats {
  constructor({ maxSamples = 64 } = {}) {
    if (!Number.isInteger(maxSamples) || maxSamples < 1 || maxSamples > 1024) throw new Error('INVALID_RTT_SAMPLE_LIMIT');
    this.maxSamples = maxSamples;
    this.samples = [];
  }

  observe(value) {
    if (!Number.isFinite(value) || value < 0 || value > 60_000) throw new Error('INVALID_RTT_SAMPLE');
    this.samples.push(value);
    if (this.samples.length > this.maxSamples) this.samples.shift();
  }

  snapshot() {
    if (!this.samples.length) return { count: 0, minimumMs: null, maximumMs: null, averageMs: null, p95Ms: null };
    const ordered = [...this.samples].sort((a, b) => a - b);
    const count = ordered.length;
    const p95Index = Math.max(0, Math.min(count - 1, Math.ceil(count * 0.95) - 1));
    return {
      count,
      minimumMs: ordered[0],
      maximumMs: ordered[count - 1],
      averageMs: ordered.reduce((sum, value) => sum + value, 0) / count,
      p95Ms: ordered[p95Index],
    };
  }
}

class CompanionRuntimeHealthTracker {
  constructor({ nowMs = () => performance.now(), maxPending = 8, maxSamples = 64 } = {}) {
    if (typeof nowMs !== 'function') throw new Error('INVALID_CLOCK');
    if (!Number.isInteger(maxPending) || maxPending < 1 || maxPending > 64) throw new Error('INVALID_PENDING_HEARTBEAT_LIMIT');
    this.nowMs = nowMs;
    this.maxPending = maxPending;
    this.pending = new Map();
    this.stats = new BoundedRttStats({ maxSamples });
  }

  heartbeatSent(messageId) {
    if (typeof messageId !== 'string' || !UUID_RE.test(messageId)) throw new Error('INVALID_HEARTBEAT_MESSAGE_ID');
    this.pending.set(messageId, this.nowMs());
    while (this.pending.size > this.maxPending) this.pending.delete(this.pending.keys().next().value);
  }

  accept(payload) {
    const health = sanitizeServerRuntimeHealth(payload);
    if (!health) return null;
    const sentAt = this.pending.get(health.heartbeatMessageId);
    if (sentAt === undefined) return null;
    this.pending.delete(health.heartbeatMessageId);
    const rttMs = this.nowMs() - sentAt;
    if (!Number.isFinite(rttMs) || rttMs < 0 || rttMs > 60_000) return null;
    this.stats.observe(rttMs);
    return { ...health, rttMs, rtt: this.stats.snapshot() };
  }

  resetPending() { this.pending.clear(); }
}

module.exports = {
  BoundedRttStats,
  CompanionRuntimeHealthTracker,
  sanitizeServerRuntimeHealth,
};
