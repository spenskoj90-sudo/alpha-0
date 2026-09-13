'use strict';

const path = require('node:path');
const { fork } = require('node:child_process');
const { sanitizePresentation } = require('./overlay-state');

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MODES = new Set(['ACTIVE', 'DEGRADED', 'STOPPED']);

function safeCount(value, max = 1_000_000) {
  return Number.isSafeInteger(value) && value >= 0 && value <= max ? value : null;
}

function safeMs(value) {
  return Number.isFinite(value) && value >= 0 && value <= 60_000 ? value : null;
}

function sanitizeRuntimeHealth(health) {
  if (!health || typeof health !== 'object' || health.healthKind !== 'runtime') return null;
  if (typeof health.connectionId !== 'string' || !UUID_RE.test(health.connectionId)) return null;
  if (typeof health.heartbeatMessageId !== 'string' || !UUID_RE.test(health.heartbeatMessageId)) return null;
  if (typeof health.mode !== 'string' || !MODES.has(health.mode)) return null;
  const reconnectAttempts = safeCount(health.reconnectAttempts, 10_000);
  const queueDepth = safeCount(health.queueDepth, 4096);
  const droppedEvents = safeCount(health.droppedEvents);
  const rttMs = safeMs(health.rttMs);
  const count = safeCount(health.rtt?.count, 1024);
  const minimumMs = health.rtt?.minimumMs === null ? null : safeMs(health.rtt?.minimumMs);
  const maximumMs = health.rtt?.maximumMs === null ? null : safeMs(health.rtt?.maximumMs);
  const averageMs = health.rtt?.averageMs === null ? null : safeMs(health.rtt?.averageMs);
  const p95Ms = health.rtt?.p95Ms === null ? null : safeMs(health.rtt?.p95Ms);
  if ([reconnectAttempts, queueDepth, droppedEvents, rttMs, count].some(value => value === null)) return null;
  if (typeof health.killSwitchActive !== 'boolean' || typeof health.peerAuthenticated !== 'boolean') return null;
  if (count > 0 && [minimumMs, maximumMs, averageMs, p95Ms].some(value => value === null)) return null;
  return {
    healthKind: 'runtime',
    connectionId: health.connectionId,
    heartbeatMessageId: health.heartbeatMessageId,
    mode: health.mode,
    reconnectAttempts,
    queueDepth,
    droppedEvents,
    killSwitchActive: health.killSwitchActive,
    peerAuthenticated: health.peerAuthenticated,
    rttMs,
    rtt: { count, minimumMs, maximumMs, averageMs, p95Ms },
  };
}

class CompanionProcessManager {
  constructor({
    workerPath = path.join(__dirname, 'companion-worker.js'),
    forkImpl = fork,
    onStatus = () => {},
    onRefreshNeeded = async () => null,
    onObservationAck = () => {},
    onObservationDeferred = () => {},
    onPresentation = () => {},
    onRuntimeHealth = () => {},
  } = {}) {
    this.workerPath = workerPath;
    this.forkImpl = forkImpl;
    this.onStatus = onStatus;
    this.onRefreshNeeded = onRefreshNeeded;
    this.onObservationAck = onObservationAck;
    this.onObservationDeferred = onObservationDeferred;
    this.onPresentation = onPresentation;
    this.onRuntimeHealth = onRuntimeHealth;
    this.child = null;
    this.status = { state: 'STOPPED', reason: 'NOT_STARTED' };
    this.expectedStop = false;
  }

  start({ coreUrl, sessionToken }) {
    if (this.child) throw new Error('COMPANION_ALREADY_RUNNING');
    if (!sessionToken) throw new Error('AUTHENTICATION_REQUIRED');
    this.expectedStop = false;
    const child = this.forkImpl(this.workerPath, [], {
      stdio: ['ignore', 'ignore', 'ignore', 'ipc'],
      windowsHide: true,
    });
    this.child = child;
    child.on('message', message => this.#onMessage(child, message));
    child.on('exit', (code, signal) => this.#onExit(child, code, signal));
    child.send({ type: 'start', coreUrl, sessionToken });
    this.#publish({ state: 'CONNECTING', reason: 'WORKER_STARTED' });
    return this.status;
  }

  updateSession(sessionToken) {
    if (this.child?.connected) this.child.send({ type: 'session', sessionToken });
  }

  sendObservation(observation) {
    if (!this.child?.connected || this.status.state !== 'ACTIVE') return false;
    if (!observation || typeof observation.event_id !== 'string') return false;
    this.child.send({ type: 'wow-observation', observation });
    return true;
  }

  stop(reason = 'STOPPED_BY_USER') {
    this.expectedStop = true;
    const child = this.child;
    this.child = null;
    if (child?.connected) child.send({ type: 'stop', reason });
    if (child && !child.killed) child.kill('SIGTERM');
    this.#publish({ state: 'STOPPED', reason });
    return this.status;
  }

  async #onMessage(source, message) {
    if (source !== this.child || !message || typeof message !== 'object') return;
    if (message.type === 'status' && message.status) {
      this.#publish(message.status);
      return;
    }
    if (message.type === 'presentation') {
      const presentation = sanitizePresentation(message.presentation);
      if (presentation) this.onPresentation(presentation);
      return;
    }
    if (message.type === 'runtime-health') {
      const health = sanitizeRuntimeHealth(message.health);
      if (health) this.onRuntimeHealth(health);
      return;
    }
    if (message.type === 'observation-ack') {
      this.onObservationAck({
        eventId: typeof message.eventId === 'string' ? message.eventId : null,
        accepted: message.accepted === true,
        reason: typeof message.reason === 'string' ? message.reason : null,
      });
      return;
    }
    if (message.type === 'observation-deferred') {
      if (typeof message.eventId === 'string') this.onObservationDeferred(message.eventId);
      return;
    }
    if (message.type === 'refresh-needed') {
      this.#publish({ state: 'DEGRADED', reason: 'SESSION_REFRESH_REQUIRED' });
      try {
        const token = await this.onRefreshNeeded();
        if (source !== this.child) return;
        if (!token) throw new Error('REFRESH_FAILED');
        this.updateSession(token);
      } catch {
        if (source === this.child) this.stop('SESSION_REFRESH_FAILED');
      }
    }
  }

  #onExit(source, code, signal) {
    if (source !== this.child) return;
    this.child = null;
    if (this.expectedStop) return;
    this.#publish({
      state: 'STOPPED',
      reason: 'WORKER_EXITED',
      exitCode: Number.isInteger(code) ? code : null,
      signal: signal || null,
    });
  }

  #publish(status) {
    this.status = sanitizeStatus(status);
    this.onStatus(this.status);
  }
}

function sanitizeStatus(status) {
  const allowed = ['state', 'reason', 'retryInMs', 'attempt', 'exitCode', 'signal'];
  const output = {};
  for (const key of allowed) {
    if (Object.prototype.hasOwnProperty.call(status || {}, key)) output[key] = status[key];
  }
  return output;
}

module.exports = { CompanionProcessManager, sanitizeRuntimeHealth, sanitizeStatus };
