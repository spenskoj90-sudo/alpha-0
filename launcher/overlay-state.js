'use strict';

const MAX_TEXT_CHARS = 2000;
const MAX_PROVENANCE_ITEMS = 20;
const MAX_PROVENANCE_CHARS = 256;
const ALLOWED_KINDS = new Set(['STATUS', 'RECOMMENDATION', 'ALERT']);

function sanitizePresentation(value) {
  if (!value || typeof value !== 'object') return null;
  if (value.channel !== 'OVERLAY' || !ALLOWED_KINDS.has(value.kind)) return null;
  if (typeof value.presentationId !== 'string' || !value.presentationId || value.presentationId.length > 128) return null;
  if (typeof value.text !== 'string' || !value.text.trim() || value.text.length > MAX_TEXT_CHARS) return null;
  if (value.confidence != null && (typeof value.confidence !== 'number' || !Number.isFinite(value.confidence) || value.confidence < 0 || value.confidence > 1)) return null;
  if (!Array.isArray(value.provenance) || value.provenance.length > MAX_PROVENANCE_ITEMS) return null;
  const provenance = [];
  for (const item of value.provenance) {
    if (typeof item !== 'string' || !item || item.length > MAX_PROVENANCE_CHARS) return null;
    provenance.push(item);
  }
  return Object.freeze({
    presentationId: value.presentationId,
    channel: 'OVERLAY',
    kind: value.kind,
    text: value.text.trim(),
    confidence: value.confidence == null ? null : value.confidence,
    provenance: Object.freeze(provenance),
  });
}

class OverlayPresentationStore {
  constructor({ maxItems = 4, ttlMs = 15000, now = () => Date.now() } = {}) {
    if (!Number.isInteger(maxItems) || maxItems < 1 || maxItems > 16) throw new Error('OVERLAY_STORE_LIMIT_INVALID');
    if (!Number.isInteger(ttlMs) || ttlMs < 1000 || ttlMs > 120000) throw new Error('OVERLAY_STORE_TTL_INVALID');
    this.maxItems = maxItems;
    this.ttlMs = ttlMs;
    this.now = now;
    this.items = [];
  }
  push(value) {
    const presentation = sanitizePresentation(value);
    if (!presentation) return false;
    const receivedAt = this.now();
    this.items = this.items.filter(item => item.presentation.presentationId !== presentation.presentationId);
    this.items.push({ presentation, receivedAt });
    if (this.items.length > this.maxItems) this.items = this.items.slice(-this.maxItems);
    return true;
  }
  clear() { this.items = []; }
  snapshot() {
    const cutoff = this.now() - this.ttlMs;
    this.items = this.items.filter(item => item.receivedAt >= cutoff);
    return this.items.map(item => item.presentation);
  }
}

module.exports = { OverlayPresentationStore, sanitizePresentation };
