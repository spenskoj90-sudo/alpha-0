'use strict';

const root = document.getElementById('overlay-root');

function cardFor(presentation) {
  const card = document.createElement('section');
  card.className = `overlay-card kind-${String(presentation.kind || '').toLowerCase()}`;

  const header = document.createElement('div');
  header.className = 'overlay-header';
  header.textContent = presentation.kind === 'ALERT'
    ? 'SENTINEL ALERT'
    : presentation.kind === 'STATUS'
      ? 'SENTINEL STATUS'
      : 'SENTINEL RECOMMENDATION';

  const text = document.createElement('div');
  text.className = 'overlay-text';
  text.textContent = String(presentation.text || '');

  card.append(header, text);
  if (typeof presentation.confidence === 'number') {
    const confidence = document.createElement('div');
    confidence.className = 'overlay-meta';
    confidence.textContent = `CONFIDENCE ${Math.round(presentation.confidence * 100)}%`;
    card.appendChild(confidence);
  }
  return card;
}

function render(snapshot) {
  root.replaceChildren();
  const items = Array.isArray(snapshot) ? snapshot.slice(-3).reverse() : [];
  for (const presentation of items) root.appendChild(cardFor(presentation));
}

window.sentinelOverlay.onSnapshot(render);
