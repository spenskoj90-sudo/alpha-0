'use strict';

const path = require('node:path');
const { fork } = require('node:child_process');
const { sanitizePresentation } = require('./presentation-runtime');

class CompanionProcessManager {
  constructor({
    workerPath = path.join(__dirname, 'companion-worker.js'),
    forkImpl = fork,
    onStatus = () => {},
    onRefreshNeeded = async () => null,
    onObservationAck = () => {},
    onObservationDeferred = () => {},
    onPresentation = () => {},
  } = {}) {
    this.workerPath = workerPath;
    this.forkImpl = forkImpl;
    this.onStatus = onStatus;
    this.onRefreshNeeded = onRefreshNeeded;
    this.onObservationAck = onObservationAck;
    this.onObservationDeferred = onObservationDeferred;
    this.onPresentation = onPresentation;
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
    child.on('message', message => this.#onMessage(message));
    child.on('exit', (code, signal) => this.#onExit(code, signal));
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

  async #onMessage(message) {
    if (!message || typeof message !== 'object') return;
    if (message.type === 'status' && message.status) {
      this.#publish(message.status);
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
    if (message.type === 'presentation') {
      try { this.onPresentation(sanitizePresentation(message.presentation)); }
      catch { this.stop('PRESENTATION_INVALID'); }
      return;
    }
    if (message.type === 'refresh-needed') {
      this.#publish({ state: 'DEGRADED', reason: 'SESSION_REFRESH_REQUIRED' });
      try {
        const token = await this.onRefreshNeeded();
        if (!token) throw new Error('REFRESH_FAILED');
        this.updateSession(token);
      } catch {
        this.stop('SESSION_REFRESH_FAILED');
      }
    }
  }

  #onExit(code, signal) {
    if (!this.child) return;
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

module.exports = { CompanionProcessManager, sanitizeStatus };
