'use strict';

const ui = window.sentinelUi;
let lastSnapshot;
const stateNode = document.getElementById('state');
const listNode = document.getElementById('presentations');
const panelNode = document.querySelector('.panel');

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function normalizeDensity(snapshot) {
  const raw = String(snapshot?.overlayDensity || snapshot?.overlay?.density || 'Standard').toUpperCase();
  return ['MINIMAL', 'STANDARD', 'EXPANDED'].includes(raw) ? raw : 'STANDARD';
}

function scenarioFor(presentation, companionState) {
  if (companionState === 'DEGRADED' || companionState === 'LOCAL-ONLY' || companionState === 'OFFLINE') return 'DEGRADED';
  if (presentation?.kind === 'ALERT') return 'WARNING';
  if (presentation?.kind === 'RECOMMENDATION') return 'RECOMMENDATION';
  return 'STATUS';
}

function render(snapshot) {
  lastSnapshot = snapshot;
  const companionState = typeof snapshot?.companion?.state === 'string' ? snapshot.companion.state : 'STOPPED';
  const checkpointState = typeof snapshot?.wow?.state === 'string' ? snapshot.wow.state : null;
  const p95 = Number.isFinite(snapshot?.runtime?.rtt?.p95Ms) ? Math.round(snapshot.runtime.rtt.p95Ms) : null;
  const density = normalizeDensity(snapshot);
  const parts = [ui.state(companionState)];
  if (checkpointState) parts.push(ui.state(checkpointState));
  if (p95 !== null) parts.push(`RTT p95 ${p95}ms`);
  stateNode.textContent = parts.join(' · ');
  panelNode?.setAttribute('data-density', density);
  clear(listNode);

  const presentations = Array.isArray(snapshot?.presentations)
    ? snapshot.presentations.filter(item => item && item.channel === 'OVERLAY')
    : [];
  const presentation = presentations.at(-1) || null;
  if (!presentation) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = ui.t(['OFFLINE', 'LOCAL-ONLY'].includes(companionState)
      ? 'No authoritative overlay presentation · {state}'
      : companionState === 'DEGRADED'
        ? 'Companion degraded · waiting for authoritative presentation.'
        : 'Waiting for Companion presentation.', { state: ui.state(companionState) });
    listNode.appendChild(empty);
    return;
  }

  const item = document.createElement('div');
  item.className = 'item';
  item.dataset.scenario = scenarioFor(presentation, companionState);

  const kind = document.createElement('div');
  kind.className = 'kind';
  kind.textContent = ui.t(presentation.evidenceKind || (typeof presentation.kind === 'string' ? presentation.kind : 'STATUS'));

  const text = document.createElement('div');
  text.className = 'text';
  text.textContent = typeof presentation.text === 'string' ? presentation.text : '';

  item.append(kind, text);

  if (density !== 'MINIMAL' && Number.isFinite(presentation.confidence)) {
    const confidence = document.createElement('div');
    confidence.className = 'meta';
    confidence.textContent = ui.t('Confidence {percent}%', { percent: Math.round(presentation.confidence * 100) });
    item.appendChild(confidence);
  }

  if (density !== 'MINIMAL' && presentation.kind === 'RECOMMENDATION' && !Number.isFinite(presentation.confidence)) {
    const unknown = document.createElement('div');
    unknown.className = 'meta';
    unknown.textContent = ui.t('Confidence unknown · no calibrated estimate');
    item.appendChild(unknown);
  }

  if (density === 'EXPANDED') {
    const provenance = document.createElement('div');
    provenance.className = 'meta';
    const source = Array.isArray(presentation.provenance) && presentation.provenance.length
      ? presentation.provenance.join(' · ')
      : ui.t('source unavailable');
    provenance.textContent = ui.t('Source: {source} · Source time: unavailable', { source });
    item.appendChild(provenance);
  }

  listNode.appendChild(item);
}

window.sentinelOverlay?.onSnapshot(render);

ui.onChange(() => { if (lastSnapshot) render(lastSnapshot); });
