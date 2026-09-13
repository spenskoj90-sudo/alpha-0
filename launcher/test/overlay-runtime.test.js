'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { OverlayPresentationStore, sanitizePresentation } = require('../overlay-state');
const { normalizeServerPresentation } = require('../companion-worker');

function presentation(id = 'p-1', overrides = {}) {
  return {
    presentationId: id,
    channel: 'OVERLAY',
    kind: 'STATUS',
    text: 'Passive WoW checkpoint accepted by Core.',
    confidence: null,
    provenance: ['sentinel-core', 'wow-passive-checkpoint'],
    ...overrides,
  };
}

test('overlay presentation sanitizer allowlists bounded read-only fields', () => {
  const safe = sanitizePresentation({ ...presentation(), command: 'cast', token: 'secret' });
  assert.deepEqual(safe, presentation());
  assert.equal(Object.prototype.hasOwnProperty.call(safe, 'command'), false);
  assert.equal(JSON.stringify(safe).includes('secret'), false);
  assert.equal(sanitizePresentation(presentation('voice', { channel: 'VOICE' })), null);
  assert.equal(sanitizePresentation(presentation('long', { text: 'x'.repeat(2001) })), null);
  assert.equal(sanitizePresentation(presentation('bad-confidence', { confidence: 2 })), null);
});

test('overlay store is bounded, deduplicated and expires stale presentations', () => {
  let now = 1000;
  const store = new OverlayPresentationStore({ maxItems: 2, ttlMs: 1000, now: () => now });
  assert.equal(store.push(presentation('a')), true);
  assert.equal(store.push(presentation('b')), true);
  assert.equal(store.push(presentation('a', { text: 'updated' })), true);
  assert.deepEqual(store.snapshot().map(item => item.presentationId), ['b', 'a']);
  assert.equal(store.push(presentation('c')), true);
  assert.deepEqual(store.snapshot().map(item => item.presentationId), ['a', 'c']);
  now = 2501;
  assert.deepEqual(store.snapshot(), []);
});

test('worker normalizes only bounded Core presentation envelopes', () => {
  const normalized = normalizeServerPresentation({
    message_type: 'HEALTH',
    payload: {
      presentation_id: 'core-presentation-1',
      channel: 'OVERLAY',
      kind: 'STATUS',
      text: 'Core status',
      confidence: null,
      provenance: ['sentinel-core'],
      action: 'execute',
    },
  });
  assert.deepEqual(normalized, {
    presentationId: 'core-presentation-1',
    channel: 'OVERLAY',
    kind: 'STATUS',
    text: 'Core status',
    confidence: null,
    provenance: ['sentinel-core'],
  });
  assert.equal(normalizeServerPresentation({ message_type: 'HEALTH', payload: { ...normalized, channel: 'VOICE' } }), null);
  assert.equal(normalizeServerPresentation({ message_type: 'WOW_OBSERVATION_ACK', payload: normalized }), null);
});

test('dedicated overlay renderer is sandboxed and contains no action IPC surface', () => {
  const root = path.resolve(__dirname, '..');
  const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
  const preload = fs.readFileSync(path.join(root, 'overlay-preload.js'), 'utf8');
  const renderer = fs.readFileSync(path.join(root, 'overlay-renderer.js'), 'utf8');
  assert.match(main, /overlay-preload\.js/);
  assert.match(main, /contextIsolation:\s*true/);
  assert.match(main, /nodeIntegration:\s*false/);
  assert.match(main, /sandbox:\s*true/);
  assert.match(main, /setIgnoreMouseEvents\(true/);
  assert.doesNotMatch(preload, /ipcRenderer\.(?:invoke|send)\s*\(/);
  assert.doesNotMatch(renderer, /innerHTML|eval\(|new Function|ipcRenderer/);
  assert.match(renderer, /textContent/);
});
