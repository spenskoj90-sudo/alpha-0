'use strict';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const PRESENTATION_KINDS = new Set(['STATUS', 'RECOMMENDATION', 'ALERT']);
const DEFAULT_TTL_MS = Object.freeze({
  STATUS: 8000,
  RECOMMENDATION: 20000,
  ALERT: 30000,
});

function sanitizePresentation(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('PRESENTATION_INVALID');
  }
  const presentationId = String(value.presentation_id || '');
  const correlationId = String(value.correlation_id || '');
  if (!UUID_RE.test(presentationId) || !UUID_RE.test(correlationId)) {
    throw new Error('PRESENTATION_ID_INVALID');
  }
  if (value.channel !== 'OVERLAY') throw new Error('PRESENTATION_CHANNEL_UNSUPPORTED');
  if (!PRESENTATION_KINDS.has(value.kind)) throw new Error('PRESENTATION_KIND_INVALID');
  if (value.action_capable !== false) throw new Error('PRESENTATION_ACTION_CAPABILITY_FORBIDDEN');
  if (typeof value.text !== 'string' || !value.text.trim() || value.text.length > 2000) {
    throw new Error('PRESENTATION_TEXT_INVALID');
  }
  const provenance = value.provenance == null ? [] : value.provenance;
  if (!Array.isArray(provenance) || provenance.length > 20) throw new Error('PRESENTATION_PROVENANCE_INVALID');
  if (provenance.some(item => typeof item !== 'string' || !item || item.length > 256)) {
    throw new Error('PRESENTATION_PROVENANCE_INVALID');
  }
  const confidence = value.confidence == null ? null : Number(value.confidence);
  if (confidence !== null && (!Number.isFinite(confidence) || confidence < 0 || confidence > 1)) {
    throw new Error('PRESENTATION_CONFIDENCE_INVALID');
  }
  return Object.freeze({
    presentation_id: presentationId,
    correlation_id: correlationId,
    channel: 'OVERLAY',
    kind: value.kind,
    text: value.text,
    confidence,
    provenance: Object.freeze([...provenance]),
    action_capable: false,
  });
}

class PresentationStore {
  constructor({
    maxItems = 8,
    ttlMs = DEFAULT_TTL_MS,
    now = Date.now,
    setTimeoutImpl = setTimeout,
    clearTimeoutImpl = clearTimeout,
    onChange = () => {},
  } = {}) {
    if (!Number.isInteger(maxItems) || maxItems < 1 || maxItems > 32) {
      throw new Error('PRESENTATION_STORE_LIMIT_INVALID');
    }
    this.maxItems = maxItems;
    this.ttlMs = { ...DEFAULT_TTL_MS, ...(ttlMs || {}) };
    for (const kind of PRESENTATION_KINDS) {
      const value = this.ttlMs[kind];
      if (!Number.isInteger(value) || value < 1000 || value > 300000) {
        throw new Error('PRESENTATION_TTL_INVALID');
      }
    }
    this.now = now;
    this.setTimeoutImpl = setTimeoutImpl;
    this.clearTimeoutImpl = clearTimeoutImpl;
    this.onChange = onChange;
    this.items = [];
    this.timers = new Map();
  }

  get depth() { return this.items.length; }

  snapshot() {
    return this.items.map(item => ({
      presentation_id: item.presentation_id,
      correlation_id: item.correlation_id,
      channel: item.channel,
      kind: item.kind,
      text: item.text,
      confidence: item.confidence,
      provenance: [...item.provenance],
      action_capable: false,
      expires_at_epoch_ms: item.expires_at_epoch_ms,
    }));
  }

  add(value) {
    const presentation = sanitizePresentation(value);
    if (this.items.some(item => item.presentation_id === presentation.presentation_id)) return false;
    while (this.items.length >= this.maxItems) this.#removeAt(0);
    const ttl = this.ttlMs[presentation.kind];
    const item = Object.freeze({
      ...presentation,
      expires_at_epoch_ms: this.now() + ttl,
    });
    this.items.push(item);
    const timer = this.setTimeoutImpl(() => this.dismiss(item.presentation_id), ttl);
    if (timer && typeof timer.unref === 'function') timer.unref();
    this.timers.set(item.presentation_id, timer);
    this.#publish();
    return true;
  }

  dismiss(presentationId) {
    const index = this.items.findIndex(item => item.presentation_id === presentationId);
    if (index < 0) return false;
    this.#removeAt(index);
    this.#publish();
    return true;
  }

  clear() {
    for (const timer of this.timers.values()) this.clearTimeoutImpl(timer);
    this.timers.clear();
    if (!this.items.length) return;
    this.items = [];
    this.#publish();
  }

  #removeAt(index) {
    const [removed] = this.items.splice(index, 1);
    if (!removed) return;
    const timer = this.timers.get(removed.presentation_id);
    if (timer !== undefined) this.clearTimeoutImpl(timer);
    this.timers.delete(removed.presentation_id);
  }

  #publish() {
    this.onChange(this.snapshot());
  }
}

module.exports = {
  DEFAULT_TTL_MS,
  PresentationStore,
  sanitizePresentation,
};
