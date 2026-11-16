'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { OverlayPresentationStore, sanitizePresentation, clearOverlayOnInactiveCompanion } = require('../overlay-state');
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

test('worker normalizes only dedicated bounded Core presentation envelopes', () => {
  const payload = {
    presentation_id: 'core-presentation-1',
    channel: 'OVERLAY',
    kind: 'STATUS',
    text: 'Core status',
    confidence: null,
    provenance: ['sentinel-core'],
    action: 'execute',
  };
  const normalized = normalizeServerPresentation({
    message_type: 'PRESENTATION',
    payload,
  });
  assert.deepEqual(normalized, {
    presentationId: 'core-presentation-1',
    channel: 'OVERLAY',
    kind: 'STATUS',
    text: 'Core status',
    confidence: null,
    provenance: ['sentinel-core'],
  });
  assert.equal(normalizeServerPresentation({ message_type: 'PRESENTATION', payload: { ...payload, channel: 'VOICE' } }), null);
  assert.equal(normalizeServerPresentation({ message_type: 'HEALTH', payload }), null);
  assert.equal(normalizeServerPresentation({ message_type: 'UGS_UPDATE', payload }), null);
  assert.equal(normalizeServerPresentation({ message_type: 'WOW_OBSERVATION_ACK', payload }), null);
});

test('dedicated overlay renderer is sandboxed, non-actionable and tied to main-window lifecycle', () => {
  const root = path.resolve(__dirname, '..');
  const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
  const preload = fs.readFileSync(path.join(root, 'overlay-preload.js'), 'utf8');
  const renderer = fs.readFileSync(path.join(root, 'overlay-renderer.js'), 'utf8');
  assert.match(main, /overlay-preload\.js/);
  assert.match(main, /contextIsolation:\s*true/);
  assert.match(main, /nodeIntegration:\s*false/);
  assert.match(main, /sandbox:\s*true/);
  assert.match(main, /setIgnoreMouseEvents\(true/);
  assert.match(main, /overlayWindow\.close\(\)/);
  assert.doesNotMatch(main, /BrowserWindow\.getAllWindows\(\)/);
  assert.doesNotMatch(preload, /ipcRenderer\.(?:invoke|send)\s*\(/);
  assert.doesNotMatch(renderer, /innerHTML|eval\(|new Function|ipcRenderer/);
  assert.match(renderer, /textContent/);
  assert.match(renderer, /No authoritative overlay presentation/);
  assert.match(renderer, /LOCAL-ONLY/);
  assert.match(renderer, /OFFLINE/);
});

test('overlay preserves fact/inference distinction without granting authority', () => {
  const value = presentation('fact', { kind: 'RECOMMENDATION', evidenceKind: 'FACT' });
  assert.equal(sanitizePresentation(value)?.evidenceKind, 'FACT');
  assert.equal(sanitizePresentation({ ...value, evidenceKind: 'EXECUTE' }), null);
  const wire = normalizeServerPresentation({ message_type: 'PRESENTATION', payload: { presentation_id: 'p', channel: 'OVERLAY', kind: 'RECOMMENDATION', knowledge_kind: 'inference', text: 'Evidence.', confidence: null, provenance: ['source'] } });
  assert.equal(wire?.evidenceKind, 'INFERENCE');
});

test('overlay advice revokes immediately on reconnecting, degraded, stopped and unknown states', () => {
  const store = new OverlayPresentationStore();
  const add = id => store.push(presentation(id, { kind: 'RECOMMENDATION' }));
  assert.equal(add('a'), true);
  assert.equal(clearOverlayOnInactiveCompanion({ state: 'ACTIVE' }, store), false);
  assert.deepEqual(store.snapshot().map(value => value.presentationId), ['a']);

  for (const state of ['DEGRADED', 'CONNECTING', 'STOPPED', 'UNKNOWN']) {
    assert.equal(clearOverlayOnInactiveCompanion({ state }, store), true, state);
    assert.deepEqual(store.snapshot(), [], state);
    assert.equal(add(state), true);
  }
  assert.equal(clearOverlayOnInactiveCompanion(null, store), true);
  assert.deepEqual(store.snapshot(), []);
  // An ACTIVE transition by itself never restores advice from a prior generation.
  assert.equal(clearOverlayOnInactiveCompanion({ state: 'ACTIVE' }, store), false);
  assert.deepEqual(store.snapshot(), []);

  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(main, /clearOverlayOnInactiveCompanion\(status, overlayStore\)/);
  assert.match(main, /companion\.status\.state !== 'ACTIVE' \|\| !overlayStore\.push\(presentation\)/);
  assert.match(main, /onRuntimeHealth: health => \{\s*if \(companion\.status\.state !== 'ACTIVE'\) return/);
});

test('overlay TTL is monotonic by default and fails closed on clock reversal or invalid clock', () => {
  let now = 5000;
  const store = new OverlayPresentationStore({ now: () => now, ttlMs: 1000 });
  assert.equal(store.push(presentation('observed')), true);
  now = 4900;
  assert.deepEqual(store.snapshot(), []);
  now = 9000;
  assert.deepEqual(store.snapshot(), []);

  const corrupt = new OverlayPresentationStore({ now: () => NaN });
  assert.equal(corrupt.push(presentation('invalid')), false);
  assert.deepEqual(corrupt.snapshot(), []);
  const source = fs.readFileSync(path.join(__dirname, '..', 'overlay-state.js'), 'utf8');
  assert.match(source, /performance\.now\(\)/);
});
