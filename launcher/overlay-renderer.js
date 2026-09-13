'use strict';

const stateNode = document.getElementById('state');
const listNode = document.getElementById('presentations');

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function render(snapshot) {
  const companionState = typeof snapshot?.companion?.state === 'string' ? snapshot.companion.state : 'STOPPED';
  const checkpointState = typeof snapshot?.wow?.state === 'string' ? snapshot.wow.state : null;
  stateNode.textContent = checkpointState ? `${companionState} · ${checkpointState}` : companionState;
  clear(listNode);
  const presentations = Array.isArray(snapshot?.presentations) ? snapshot.presentations.slice(-4) : [];
  if (!presentations.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = 'Waiting for Companion presentation.';
    listNode.appendChild(empty);
    return;
  }
  for (const presentation of presentations) {
    if (!presentation || presentation.channel !== 'OVERLAY') continue;
    const item = document.createElement('div');
    item.className = 'item';
    const kind = document.createElement('div');
    kind.className = 'kind';
    kind.textContent = typeof presentation.kind === 'string' ? presentation.kind : 'STATUS';
    const text = document.createElement('div');
    text.className = 'text';
    text.textContent = typeof presentation.text === 'string' ? presentation.text : '';
    item.append(kind, text);
    listNode.appendChild(item);
  }
}

window.sentinelOverlay?.onSnapshot(render);
