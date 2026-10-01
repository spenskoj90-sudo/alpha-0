'use strict';

const navigationLinks = Array.from(document.querySelectorAll('.nav a[href^="#"]'));

function syncNavigation() {
  const target = window.location.hash || '#overview';
  for (const link of navigationLinks) {
    if (link.getAttribute('href') === target) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  }
}

window.addEventListener('hashchange', syncNavigation);
syncNavigation();

const accountPanel = document.getElementById('account-panel');
const accountStatus = document.getElementById('account-status');
const statusIds = ['account-status', 'companion-status', 'wow-checkpoint-status', 'connection-status', 'voice-status', 'voice-result'];

function syncStatusTone(node) {
  if (!node) return;
  const failed = node.classList.contains('err');
  node.setAttribute('role', failed ? 'alert' : 'status');
  node.setAttribute('aria-live', failed ? 'assertive' : 'polite');
  node.setAttribute('aria-atomic', 'true');
}

for (const id of statusIds) {
  const node = document.getElementById(id);
  if (!node) continue;
  syncStatusTone(node);
  new MutationObserver(() => syncStatusTone(node)).observe(node, {
    attributes: true,
    attributeFilter: ['class'],
    childList: true,
  });
}

function setAccountBusy(busy) {
  accountPanel?.setAttribute('aria-busy', busy ? 'true' : 'false');
}

for (const id of ['login', 'logout']) {
  document.getElementById(id)?.addEventListener('click', () => setAccountBusy(true));
}

if (accountStatus && accountPanel) {
  new MutationObserver(() => setAccountBusy(false)).observe(accountStatus, {
    attributes: true,
    attributeFilter: ['class'],
    childList: true,
  });
}
