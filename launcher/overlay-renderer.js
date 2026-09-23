'use strict';

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
  const companionState = typeof snapshot?.companion?.state === 'string' ? snapshot.companion.state : 'STOPPED';
  const checkpointState = typeof snapshot?.wow?.state === 'string' ? snapshot.wow.state : null;
  const p95 = Number.isFinite(snapshot?.runtime?.rtt?.p95Ms) ? Math.round(snapshot.runtime.rtt.p95Ms) : null;
  const density = normalizeDensity(snapshot);
  const parts = [companionState];
  if (checkpointState) parts.push(checkpointState);
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
    empty.textContent = 'Waiting for Companion presentation.';
    listNode.appendChild(empty);
    return;
  }

  const item = document.createElement('div');
  item.className = 'item';
  item.dataset.scenario = scenarioFor(presentation, companionState);

  const kind = document.createElement('div');
  kind.className = 'kind';
  kind.textContent = typeof presentation.kind === 'string' ? presentation.kind : 'STATUS';

  const text = document.createElement('div');
  text.className = 'text';
  text.textContent = typeof presentation.text === 'string' ? presentation.text : '';

  item.append(kind, text);

  if (density !== 'MINIMAL' && Number.isFinite(presentation.confidence)) {
    const confidence = document.createElement('div');
    confidence.className = 'meta';
    confidence.textContent = `Confidence ${Math.round(presentation.confidence * 100)}%`;
    item.appendChild(confidence);
  }

  if (density === 'EXPANDED') {
    const provenance = document.createElement('div');
    provenance.className = 'meta';
    const source = Array.isArray(presentation.provenance) && presentation.provenance.length
      ? presentation.provenance.join(' · ')
      : 'source unavailable';
    provenance.textContent = `Source: ${source} · Source time: unavailable`;
    item.appendChild(provenance);
  }

  listNode.appendChild(item);
}

window.sentinelOverlay?.onSnapshot(render);
