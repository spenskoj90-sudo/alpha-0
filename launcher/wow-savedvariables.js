'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const MAX_FILE_BYTES = 256 * 1024;
const MAX_TOKENS = 10000;
const MAX_DEPTH = 8;
const ALLOWED_PATCHES = new Set([
  'retail-12.0.5', 'vanilla-1.12', 'tbc-2.4.3', 'wotlk-3.3.5a',
  'cataclysm-4.3.4', 'mop-5.4.8', 'wod-6.2.4', 'legion-7.3.5',
  'bfa-8.3.7', 'shadowlands-9.2.7', 'dragonflight-10.2.7',
]);
const ALLOWED_SERVER_PROFILES = new Set(['official', 'private', 'unknown']);
const ALLOWED_COMBAT_STATES = new Set(['COMBAT', 'IDLE', 'UNKNOWN']);

function tokenizeLua(input) {
  if (typeof input !== 'string' || Buffer.byteLength(input, 'utf8') > MAX_FILE_BYTES) {
    throw new Error('SAVEDVARIABLES_FILE_TOO_LARGE');
  }
  const tokens = [];
  let i = 0;
  const push = (type, value = null) => {
    tokens.push({ type, value });
    if (tokens.length > MAX_TOKENS) throw new Error('SAVEDVARIABLES_TOKEN_LIMIT');
  };
  while (i < input.length) {
    const ch = input[i];
    if (/\s/.test(ch)) { i += 1; continue; }
    if (ch === '-' && input[i + 1] === '-') {
      i += 2;
      while (i < input.length && input[i] !== '\n') i += 1;
      continue;
    }
    if ('{}[]=,;'.includes(ch)) { push(ch, ch); i += 1; continue; }
    if (ch === '"' || ch === "'") {
      const quote = ch;
      i += 1;
      let out = '';
      while (i < input.length) {
        const current = input[i++];
        if (current === quote) break;
        if (current !== '\\') { out += current; continue; }
        if (i >= input.length) throw new Error('SAVEDVARIABLES_INVALID_ESCAPE');
        const escaped = input[i++];
        const common = { n: '\n', r: '\r', t: '\t', '\\': '\\', '"': '"', "'": "'" };
        if (Object.prototype.hasOwnProperty.call(common, escaped)) out += common[escaped];
        else if (/\d/.test(escaped)) {
          let digits = escaped;
          while (digits.length < 3 && i < input.length && /\d/.test(input[i])) digits += input[i++];
          const code = Number(digits);
          if (code > 255) throw new Error('SAVEDVARIABLES_INVALID_ESCAPE');
          out += String.fromCharCode(code);
        } else throw new Error('SAVEDVARIABLES_UNSUPPORTED_ESCAPE');
        if (out.length > 2048) throw new Error('SAVEDVARIABLES_STRING_LIMIT');
      }
      if (input[i - 1] !== quote) throw new Error('SAVEDVARIABLES_UNTERMINATED_STRING');
      push('string', out);
      continue;
    }
    const number = input.slice(i).match(/^-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/);
    if (number) {
      const value = Number(number[0]);
      if (!Number.isFinite(value)) throw new Error('SAVEDVARIABLES_INVALID_NUMBER');
      push('number', value);
      i += number[0].length;
      continue;
    }
    const ident = input.slice(i).match(/^[A-Za-z_][A-Za-z0-9_]*/);
    if (ident) { push('ident', ident[0]); i += ident[0].length; continue; }
    throw new Error('SAVEDVARIABLES_UNSUPPORTED_TOKEN');
  }
  push('eof');
  return tokens;
}

function parseSavedVariables(input) {
  const tokens = tokenizeLua(input);
  let position = 0;
  const peek = (offset = 0) => tokens[position + offset] || { type: 'eof', value: null };
  const take = expected => {
    const token = peek();
    if (expected && token.type !== expected) throw new Error(`SAVEDVARIABLES_EXPECTED_${expected}`);
    position += 1;
    return token;
  };
  const parseValue = depth => {
    if (depth > MAX_DEPTH) throw new Error('SAVEDVARIABLES_DEPTH_LIMIT');
    const token = peek();
    if (token.type === 'string' || token.type === 'number') return take().value;
    if (token.type === 'ident') {
      const value = take('ident').value;
      if (value === 'true') return true;
      if (value === 'false') return false;
      if (value === 'nil') return null;
      throw new Error('SAVEDVARIABLES_UNSUPPORTED_VALUE');
    }
    if (token.type !== '{') throw new Error('SAVEDVARIABLES_UNSUPPORTED_VALUE');
    take('{');
    const output = {};
    let arrayIndex = 1;
    while (peek().type !== '}') {
      if (peek().type === 'eof') throw new Error('SAVEDVARIABLES_UNTERMINATED_TABLE');
      let key;
      if (peek().type === '[') {
        take('[');
        const keyToken = take();
        if (!['string', 'number'].includes(keyToken.type)) throw new Error('SAVEDVARIABLES_INVALID_KEY');
        key = String(keyToken.value);
        take(']');
        take('=');
      } else if (peek().type === 'ident' && peek(1).type === '=') {
        key = String(take('ident').value);
        take('=');
      } else {
        key = String(arrayIndex++);
      }
      if (key.length > 128) throw new Error('SAVEDVARIABLES_KEY_LIMIT');
      output[key] = parseValue(depth + 1);
      if (peek().type === ',' || peek().type === ';') take();
    }
    take('}');
    return output;
  };

  const assignments = {};
  while (peek().type !== 'eof') {
    const name = take('ident').value;
    take('=');
    assignments[name] = parseValue(0);
    if (peek().type === ';' || peek().type === ',') take();
  }
  return assignments;
}

function normalizeSnapshot(savedVariables) {
  const snapshot = savedVariables?.SentinelDB?.snapshot;
  if (!snapshot || typeof snapshot !== 'object' || Array.isArray(snapshot)) throw new Error('SENTINEL_SNAPSHOT_MISSING');
  const schemaVersion = Number(snapshot.schema_version);
  const sequence = Number(snapshot.sequence);
  const observedEpoch = Number(snapshot.observed_at_epoch);
  const patchProfile = String(snapshot.patch_profile || '');
  const serverProfile = String(snapshot.server_profile || 'unknown').toLowerCase();
  const combatState = String(snapshot.combat_state || 'UNKNOWN').toUpperCase();
  const latency = Number(snapshot.latency_ms);
  if (schemaVersion !== 1) throw new Error('SENTINEL_SNAPSHOT_SCHEMA_UNSUPPORTED');
  if (!Number.isSafeInteger(sequence) || sequence < 0) throw new Error('SENTINEL_SNAPSHOT_SEQUENCE_INVALID');
  if (!Number.isSafeInteger(observedEpoch) || observedEpoch <= 0) throw new Error('SENTINEL_SNAPSHOT_TIME_INVALID');
  if (!ALLOWED_PATCHES.has(patchProfile)) throw new Error('SENTINEL_SNAPSHOT_PATCH_INVALID');
  if (!ALLOWED_SERVER_PROFILES.has(serverProfile)) throw new Error('SENTINEL_SNAPSHOT_SERVER_PROFILE_INVALID');
  if (!ALLOWED_COMBAT_STATES.has(combatState)) throw new Error('SENTINEL_SNAPSHOT_COMBAT_STATE_INVALID');
  if (!Number.isInteger(latency) || latency < 0 || latency > 60000) throw new Error('SENTINEL_SNAPSHOT_LATENCY_INVALID');
  const realmId = typeof snapshot.realm_id === 'string' ? snapshot.realm_id.trim() : '';
  if (!realmId || realmId.length > 128 || /[\u0000-\u001f]/.test(realmId)) throw new Error('SENTINEL_SNAPSHOT_REALM_INVALID');
  const material = JSON.stringify({ schemaVersion, sequence, observedEpoch, patchProfile, serverProfile, realmId, latency, combatState });
  const eventId = `wow-checkpoint-${crypto.createHash('sha256').update(material).digest('hex').slice(0, 32)}`;
  return {
    event_id: eventId,
    observed_at: new Date(observedEpoch * 1000).toISOString(),
    sequence,
    patch_profile: patchProfile,
    server_profile: serverProfile,
    realm_id: realmId,
    latency_ms: latency,
    addon_connected: snapshot.addon_connected === true,
    launcher_associated: true,
    combat_state: combatState,
    data_quality: 'LOW',
    provenance: ['sentinel-addon-savedvariables', 'sentinel-launcher-checkpoint'],
  };
}

class WowObservationQueue {
  constructor({ filePath, maxItems = 128, fsImpl = fs } = {}) {
    if (!filePath || !path.isAbsolute(filePath)) throw new Error('WOW_QUEUE_PATH_REQUIRED');
    if (!Number.isInteger(maxItems) || maxItems < 1 || maxItems > 4096) throw new Error('WOW_QUEUE_LIMIT_INVALID');
    this.filePath = filePath;
    this.maxItems = maxItems;
    this.fs = fsImpl;
    this.items = [];
    this.dropped = 0;
    this.#load();
  }
  get depth() { return this.items.length; }
  peek() { return this.items[0] || null; }
  enqueue(observation) {
    if (!observation?.event_id) throw new Error('WOW_OBSERVATION_INVALID');
    if (this.items.some(item => item.event_id === observation.event_id)) return false;
    if (this.items.length >= this.maxItems) { this.items.shift(); this.dropped += 1; }
    this.items.push(observation);
    this.#persist();
    return true;
  }
  acknowledge(eventId) {
    if (!this.items.length || this.items[0].event_id !== eventId) return false;
    this.items.shift();
    this.#persist();
    return true;
  }
  #load() {
    try {
      const parsed = JSON.parse(this.fs.readFileSync(this.filePath, 'utf8'));
      if (Array.isArray(parsed)) this.items = parsed.filter(item => item && typeof item.event_id === 'string').slice(-this.maxItems);
    } catch { this.items = []; }
  }
  #persist() {
    const directory = path.dirname(this.filePath);
    this.fs.mkdirSync(directory, { recursive: true });
    const temp = `${this.filePath}.tmp`;
    this.fs.writeFileSync(temp, JSON.stringify(this.items), { encoding: 'utf8', mode: 0o600 });
    this.fs.renameSync(temp, this.filePath);
    try { this.fs.chmodSync(this.filePath, 0o600); } catch {}
  }
}

function discoverSentinelSavedVariables(executablePath, overridePath = null, fsImpl = fs) {
  if (overridePath) {
    if (!path.isAbsolute(overridePath) || path.basename(overridePath).toLowerCase() !== 'sentinel.lua') return null;
    try { return fsImpl.statSync(overridePath).isFile() ? overridePath : null; } catch { return null; }
  }
  if (!executablePath || !path.isAbsolute(executablePath)) return null;
  const accountRoot = path.join(path.dirname(executablePath), 'WTF', 'Account');
  let accounts;
  try { accounts = fsImpl.readdirSync(accountRoot, { withFileTypes: true }); } catch { return null; }
  const candidates = [];
  for (const entry of accounts) {
    if (!entry.isDirectory()) continue;
    const candidate = path.join(accountRoot, entry.name, 'SavedVariables', 'Sentinel.lua');
    try {
      const stat = fsImpl.statSync(candidate);
      if (stat.isFile() && stat.size <= MAX_FILE_BYTES) candidates.push({ candidate, mtimeMs: stat.mtimeMs });
    } catch {}
  }
  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return candidates[0]?.candidate || null;
}

class WowCheckpointBridge {
  constructor({ queue, resolvePath, sendObservation, onStatus = () => {}, fsImpl = fs, setIntervalImpl = setInterval, clearIntervalImpl = clearInterval, intervalMs = 5000 } = {}) {
    this.queue = queue;
    this.resolvePath = resolvePath;
    this.sendObservation = sendObservation;
    this.onStatus = onStatus;
    this.fs = fsImpl;
    this.setIntervalImpl = setIntervalImpl;
    this.clearIntervalImpl = clearIntervalImpl;
    this.intervalMs = intervalMs;
    this.running = false;
    this.timer = null;
    this.signature = null;
    this.inFlight = null;
    this.companionActive = false;
  }
  start() {
    if (this.running) return;
    this.running = true;
    this.poll();
    this.timer = this.setIntervalImpl(() => this.poll(), this.intervalMs);
  }
  stop() {
    this.running = false;
    if (this.timer) this.clearIntervalImpl(this.timer);
    this.timer = null;
    this.inFlight = null;
    this.#publish('STOPPED');
  }
  onCompanionStatus(status) {
    this.companionActive = status?.state === 'ACTIVE';
    if (!this.companionActive) this.inFlight = null;
    else this.flush();
  }
  poll() {
    if (!this.running) return;
    const source = this.resolvePath?.();
    if (!source) { this.#publish('WAITING_FOR_SAVEDVARIABLES'); return; }
    try {
      const stat = this.fs.statSync(source);
      if (!stat.isFile() || stat.size > MAX_FILE_BYTES) throw new Error('SAVEDVARIABLES_FILE_TOO_LARGE');
      const signature = `${stat.size}:${stat.mtimeMs}`;
      if (signature !== this.signature) {
        const parsed = parseSavedVariables(this.fs.readFileSync(source, 'utf8'));
        const observation = normalizeSnapshot(parsed);
        this.signature = signature;
        this.queue.enqueue(observation);
      }
      this.#publish('READY');
      this.flush();
    } catch (error) {
      this.#publish('CHECKPOINT_REJECTED', { reason: error?.message || 'CHECKPOINT_REJECTED' });
    }
  }
  flush() {
    if (!this.running || !this.companionActive || this.inFlight) return false;
    const observation = this.queue.peek();
    if (!observation) return false;
    if (!this.sendObservation?.(observation)) return false;
    this.inFlight = observation.event_id;
    this.#publish('DELIVERING', { eventId: observation.event_id });
    return true;
  }
  acknowledge(eventId, accepted, reason = null) {
    if (!eventId || this.inFlight !== eventId) return false;
    this.queue.acknowledge(eventId);
    this.inFlight = null;
    this.#publish(accepted ? 'DELIVERED' : 'CORE_REJECTED', { eventId, reason });
    this.flush();
    return true;
  }
  defer(eventId) {
    if (this.inFlight === eventId) this.inFlight = null;
    this.#publish('DEFERRED', { eventId });
  }
  #publish(state, extra = {}) {
    this.onStatus({ state, queueDepth: this.queue.depth, dropped: this.queue.dropped, ...extra });
  }
}

module.exports = {
  MAX_FILE_BYTES,
  WowCheckpointBridge,
  WowObservationQueue,
  discoverSentinelSavedVariables,
  normalizeSnapshot,
  parseSavedVariables,
  tokenizeLua,
};
