'use strict';

const { randomUUID } = require('node:crypto');
const { performance } = require('node:perf_hooks');
const { URL } = require('node:url');
const { sanitizePresentation } = require('./overlay-state');
const { CompanionRuntimeHealthTracker } = require('./runtime-health');

const HANDSHAKE = Object.freeze({
  protocol_version: '1.0',
  ugs_schema_version: '1.0',
  adapter_contract_version: '1.0',
  core_protocol_version: '1.0',
  capability_profile: 'wow.passive.v1',
});
const TERMINAL_POLICY_REASONS = new Set(['COMPANION_ENTITLEMENT_REQUIRED', 'COMPANION_ENTITLEMENT_REVOKED']);

function requireLoopbackCore(value) {
  const url = new URL(String(value || ''));
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('INVALID_CORE_URL');
  const host = url.hostname.toLowerCase();
  if (!['127.0.0.1', 'localhost', '::1', '[::1]'].includes(host)) throw new Error('COMPANION_CORE_MUST_BE_LOOPBACK');
  return url;
}

function websocketUrl(coreUrl) {
  const url = requireLoopbackCore(coreUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/v1/companion/ws';
  url.search = '';
  url.hash = '';
  return url.toString();
}

function authProtocols(token) {
  if (typeof token !== 'string' || token.length < 16 || token.length > 4096) throw new Error('INVALID_SESSION_TOKEN');
  const encoded = Buffer.from(token, 'utf8').toString('base64url');
  return ['sentinel.v1', `sentinel.auth.${encoded}`];
}

function wowObservationEnvelope(observation, sequence) {
  if (!observation || typeof observation !== 'object' || typeof observation.event_id !== 'string') {
    throw new Error('INVALID_WOW_OBSERVATION');
  }
  if (!Number.isSafeInteger(sequence) || sequence < 0) throw new Error('INVALID_SEQUENCE');
  return {
    message_id: randomUUID(),
    sequence,
    message_type: 'WOW_OBSERVATION',
    latency_class: 'BACKGROUND',
    payload: observation,
  };
}

function normalizeServerPresentation(message) {
  if (!message || typeof message !== 'object' || message.message_type !== 'PRESENTATION') return null;
  const payload = message.payload;
  if (!payload || typeof payload !== 'object') return null;
  return sanitizePresentation({
    presentationId: payload.presentation_id,
    channel: payload.channel,
    kind: payload.kind,
    text: payload.text,
    confidence: payload.confidence ?? null,
    provenance: Array.isArray(payload.provenance) ? payload.provenance : [],
  });
}

class ReconnectPolicy {
  constructor({ baseMs = 1000, maxMs = 30000, maxAttempts = 8 } = {}) {
    this.baseMs = baseMs;
    this.maxMs = maxMs;
    this.maxAttempts = maxAttempts;
  }
  delay(attempt) {
    if (!Number.isInteger(attempt) || attempt < 1) throw new Error('INVALID_RECONNECT_ATTEMPT');
    return Math.min(this.maxMs, this.baseMs * (2 ** (attempt - 1)));
  }
  canRetry(attempt) { return attempt < this.maxAttempts; }
}

class CompanionWorkerRuntime {
  constructor({
    WebSocketImpl = globalThis.WebSocket,
    send = message => process.send?.(message),
    setTimeoutImpl = setTimeout,
    clearTimeoutImpl = clearTimeout,
    setIntervalImpl = setInterval,
    clearIntervalImpl = clearInterval,
    reconnectPolicy = new ReconnectPolicy(),
    nowMs = () => performance.now(),
  } = {}) {
    if (typeof WebSocketImpl !== 'function') throw new Error('WEBSOCKET_UNAVAILABLE');
    this.WebSocketImpl = WebSocketImpl;
    this.send = send;
    this.setTimeoutImpl = setTimeoutImpl;
    this.clearTimeoutImpl = clearTimeoutImpl;
    this.setIntervalImpl = setIntervalImpl;
    this.clearIntervalImpl = clearIntervalImpl;
    this.reconnectPolicy = reconnectPolicy;
    this.runtimeHealth = new CompanionRuntimeHealthTracker({ nowMs });
    this.socket = null;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.running = false;
    this.killSwitch = false;
    this.handshaken = false;
    this.sequence = 0;
    this.attempt = 0;
    this.coreUrl = null;
    this.token = null;
    this.state = 'STOPPED';
    this.reason = 'NOT_STARTED';
  }

  start({ coreUrl, sessionToken }) {
    requireLoopbackCore(coreUrl);
    authProtocols(sessionToken);
    this.running = true;
    this.killSwitch = false;
    this.coreUrl = coreUrl;
    this.token = sessionToken;
    this.attempt = 0;
    this.runtimeHealth.resetPending();
    this.#connect();
  }

  updateSession(sessionToken) {
    authProtocols(sessionToken);
    this.token = sessionToken;
    if (this.running && (!this.socket || this.socket.readyState === this.WebSocketImpl.CLOSED)) {
      this.attempt = 0;
      this.#connect();
    }
  }

  sendWowObservation(observation) {
    const eventId = typeof observation?.event_id === 'string' ? observation.event_id : null;
    const socket = this.socket;
    if (!eventId) return false;
    if (!this.running || this.killSwitch || !this.handshaken || !socket || socket.readyState !== this.WebSocketImpl.OPEN) {
      this.send({ type: 'observation-deferred', eventId });
      return false;
    }
    this.sequence += 1;
    socket.send(JSON.stringify(wowObservationEnvelope(observation, this.sequence)));
    return true;
  }

  stop(reason = 'STOPPED_BY_USER') {
    this.running = false;
    this.killSwitch = true;
    this.runtimeHealth.resetPending();
    this.#clearTimers();
    const socket = this.socket;
    this.socket = null;
    if (socket && socket.readyState < this.WebSocketImpl.CLOSING) socket.close(1000, reason);
    this.#setState('STOPPED', reason);
  }

  #connect() {
    if (!this.running || this.killSwitch) return;
    this.#clearReconnect();
    this.runtimeHealth.resetPending();
    this.#setState(this.attempt === 0 ? 'CONNECTING' : 'DEGRADED', this.attempt === 0 ? 'CONNECTING' : 'RECONNECTING');
    const socket = new this.WebSocketImpl(websocketUrl(this.coreUrl), authProtocols(this.token));
    this.socket = socket;
    this.handshaken = false;

    socket.addEventListener('open', () => {
      this.attempt = 0;
      socket.send(JSON.stringify({ ...HANDSHAKE, instance_id: randomUUID() }));
    });
    socket.addEventListener('message', event => this.#onMessage(event.data));
    socket.addEventListener('error', () => this.#setState('DEGRADED', 'TRANSPORT_ERROR'));
    socket.addEventListener('close', event => this.#onClose(event));
  }

  #onMessage(raw) {
    let message;
    try { message = JSON.parse(String(raw)); } catch {
      this.stop('INVALID_SERVER_MESSAGE');
      return;
    }
    if (!this.handshaken) {
      if (message?.accepted === true && message?.mode === 'ACTIVE') {
        this.handshaken = true;
        this.#setState('ACTIVE', 'HANDSHAKE_ACCEPTED');
        this.#startHeartbeat();
      } else {
        this.stop(String(message?.reason_code || 'HANDSHAKE_REJECTED'));
      }
      return;
    }
    if (message?.message_type === 'WOW_OBSERVATION_ACK') {
      const eventId = typeof message?.payload?.event_id === 'string' ? message.payload.event_id : null;
      if (!eventId) return;
      this.send({
        type: 'observation-ack',
        eventId,
        accepted: message.payload.accepted === true,
        reason: typeof message.payload.reason === 'string' ? message.payload.reason : null,
      });
      return;
    }
    if (message?.message_type === 'HEALTH') {
      const health = this.runtimeHealth.accept(message.payload);
      if (health) {
        this.send({ type: 'runtime-health', health });
        return;
      }
    }
    const presentation = normalizeServerPresentation(message);
    if (presentation) this.send({ type: 'presentation', presentation });
  }

  #onClose(event) {
    this.socket = null;
    this.handshaken = false;
    this.runtimeHealth.resetPending();
    this.#clearHeartbeat();
    const reason = String(event?.reason || 'TRANSPORT_CLOSED');
    if (!this.running || this.killSwitch) return;
    if (TERMINAL_POLICY_REASONS.has(reason)) {
      this.running = false;
      this.#setState('STOPPED', reason);
      return;
    }
    if (reason === 'INVALID_SESSION' || reason === 'AUTHENTICATION_REQUIRED') {
      this.#setState('DEGRADED', 'SESSION_REFRESH_REQUIRED');
      this.send({ type: 'refresh-needed' });
      return;
    }
    this.attempt += 1;
    if (!this.reconnectPolicy.canRetry(this.attempt)) {
      this.running = false;
      this.#setState('STOPPED', 'RECONNECT_BUDGET_EXHAUSTED');
      return;
    }
    const delayMs = this.reconnectPolicy.delay(this.attempt);
    this.#setState('DEGRADED', 'RECONNECT_SCHEDULED', { retryInMs: delayMs, attempt: this.attempt });
    this.reconnectTimer = this.setTimeoutImpl(() => this.#connect(), delayMs);
  }

  #startHeartbeat() {
    this.#clearHeartbeat();
    this.heartbeatTimer = this.setIntervalImpl(() => {
      const socket = this.socket;
      if (!socket || socket.readyState !== this.WebSocketImpl.OPEN || !this.handshaken) return;
      this.sequence += 1;
      const messageId = randomUUID();
      this.runtimeHealth.heartbeatSent(messageId);
      socket.send(JSON.stringify({
        message_id: messageId,
        sequence: this.sequence,
        message_type: 'HEARTBEAT',
        latency_class: 'RESPONSIVE',
        payload: {},
      }));
    }, 5000);
  }

  #setState(state, reason, extra = {}) {
    this.state = state;
    this.reason = reason;
    this.send({ type: 'status', status: { state, reason, ...extra } });
  }

  #clearHeartbeat() {
    if (this.heartbeatTimer) this.clearIntervalImpl(this.heartbeatTimer);
    this.heartbeatTimer = null;
  }
  #clearReconnect() {
    if (this.reconnectTimer) this.clearTimeoutImpl(this.reconnectTimer);
    this.reconnectTimer = null;
  }
  #clearTimers() { this.#clearHeartbeat(); this.#clearReconnect(); }
}

if (require.main === module) {
  const runtime = new CompanionWorkerRuntime();
  process.on('message', message => {
    if (!message || typeof message !== 'object') return;
    if (message.type === 'start') runtime.start(message);
    else if (message.type === 'session') runtime.updateSession(message.sessionToken);
    else if (message.type === 'wow-observation') runtime.sendWowObservation(message.observation);
    else if (message.type === 'stop') runtime.stop(message.reason);
  });
  process.on('disconnect', () => runtime.stop('PARENT_DISCONNECTED'));
  process.on('SIGTERM', () => { runtime.stop('SIGTERM'); process.exit(0); });
}

module.exports = {
  CompanionWorkerRuntime,
  ReconnectPolicy,
  authProtocols,
  normalizeServerPresentation,
  requireLoopbackCore,
  websocketUrl,
  wowObservationEnvelope,
  HANDSHAKE,
  TERMINAL_POLICY_REASONS,
};
