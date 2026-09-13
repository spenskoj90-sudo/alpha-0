'use strict';

const $ = id => document.getElementById(id);
const accountStatus = $('account-status');
const companionStatus = $('companion-status');
const wowCheckpointStatus = $('wow-checkpoint-status');
const playerOverlayStatus = $('player-overlay-status');
const loginButton = $('login');
const logoutButton = $('logout');
const startButton = $('companion-start');
const stopButton = $('companion-stop');
let signedIn = false;
let companionState = 'STOPPED';
let grantedFeatures = [];

function refreshButtons() {
  loginButton.disabled = signedIn;
  logoutButton.disabled = !signedIn;
  startButton.disabled = !signedIn || companionState !== 'STOPPED' || !grantedFeatures.includes('companion');
  stopButton.disabled = companionState === 'STOPPED';
}

function setAccount(status, features = []) {
  signedIn = Boolean(status?.authenticated);
  grantedFeatures = signedIn && Array.isArray(features) ? [...features] : [];
  accountStatus.className = `status ${signedIn ? 'ok' : ''}`;
  accountStatus.textContent = signedIn
    ? `ACCOUNT: AUTHENTICATED / ${grantedFeatures.includes('companion') ? 'COMPANION ENTITLED' : 'COMPANION NOT ENTITLED'}`
    : 'ACCOUNT: SIGNED OUT';
  refreshButtons();
}

function setCompanion(status) {
  companionState = status?.state || 'STOPPED';
  const reason = status?.reason ? ` / ${status.reason}` : '';
  companionStatus.className = `status ${companionState === 'ACTIVE' ? 'ok' : companionState === 'DEGRADED' ? 'warn' : ''}`;
  companionStatus.textContent = `COMPANION: ${companionState}${reason}`;
  refreshButtons();
}

function setWowCheckpoint(status) {
  const state = status?.state || 'STOPPED';
  const depth = Number.isInteger(status?.queueDepth) ? ` / QUEUE ${status.queueDepth}` : '';
  const reason = status?.reason ? ` / ${status.reason}` : '';
  const healthy = ['READY', 'DELIVERED'].includes(state);
  const warning = ['WAITING_FOR_SAVEDVARIABLES', 'DEFERRED', 'DELIVERING'].includes(state);
  wowCheckpointStatus.className = `status ${healthy ? 'ok' : warning ? 'warn' : state === 'STOPPED' ? '' : 'err'}`;
  wowCheckpointStatus.textContent = `WOW CHECKPOINT: ${state}${depth}${reason}`;
}

function setOverlayStatus(status) {
  const count = Number.isInteger(status?.count) && status.count >= 0 ? status.count : 0;
  const visible = status?.visible === true && count > 0;
  playerOverlayStatus.className = `status ${visible ? 'ok' : ''}`;
  playerOverlayStatus.textContent = visible
    ? `PLAYER OVERLAY: ACTIVE / ${count} ITEM${count === 1 ? '' : 'S'}`
    : 'PLAYER OVERLAY: IDLE';
}

function showError(target, error) {
  target.className = 'status err';
  target.textContent = String(error?.message || error || 'UNKNOWN_ERROR');
}

async function renderGames() {
  const [catalog, config] = await Promise.all([window.sentinel.catalog(), window.sentinel.getConfig()]);
  const grid = $('grid');
  grid.replaceChildren();
  for (const game of catalog) {
    const card = document.createElement('section');
    card.className = 'card';
    const title = document.createElement('strong');
    title.textContent = game.name;
    const platform = document.createElement('div');
    platform.className = 'sub';
    platform.textContent = String(game.platform || '').toUpperCase();
    card.append(title, platform);

    const button = document.createElement('button');
    button.className = 'btn';
    button.textContent = game.platform === 'android' ? 'USE ANDROID CLIENT' : 'LAUNCH';
    button.disabled = game.platform === 'android';
    button.onclick = async () => {
      try { await window.sentinel.launch(game.id); } catch (error) { window.alert(String(error?.message || error)); }
    };
    card.appendChild(button);

    if (game.platform === 'windows') {
      const configured = document.createElement('div');
      configured.className = 'sub';
      configured.style.marginTop = '12px';
      configured.textContent = config[game.id] ? 'EXECUTABLE CONFIGURED' : 'EXECUTABLE NOT CONFIGURED';
      card.appendChild(configured);
    }
    grid.appendChild(card);
  }
}

loginButton.onclick = async () => {
  loginButton.disabled = true;
  try {
    const result = await window.sentinel.login($('core-url').value, $('email').value, $('password').value);
    $('password').value = '';
    setAccount(result.session, result.features || []);
  } catch (error) {
    loginButton.disabled = false;
    showError(accountStatus, error);
  }
};

logoutButton.onclick = async () => {
  await window.sentinel.logout();
  setCompanion({ state: 'STOPPED', reason: 'ACCOUNT_LOGOUT' });
  setWowCheckpoint({ state: 'STOPPED', queueDepth: 0 });
  setOverlayStatus({ visible: false, count: 0 });
  setAccount(null, []);
};

startButton.onclick = async () => {
  startButton.disabled = true;
  try { setCompanion(await window.sentinel.startCompanion($('core-url').value)); }
  catch (error) { showError(companionStatus, error); refreshButtons(); }
};
stopButton.onclick = async () => {
  setWowCheckpoint({ state: 'STOPPED' });
  setOverlayStatus({ visible: false, count: 0 });
  setCompanion(await window.sentinel.stopCompanion());
};

window.sentinel.onCompanionStatus(setCompanion);
window.sentinel.onAccountStatus(snapshot => setAccount(snapshot?.session, snapshot?.features || []));
window.sentinel.onWowCheckpointStatus(setWowCheckpoint);
window.sentinel.onOverlayStatus(setOverlayStatus);

Promise.all([window.sentinel.accountStatus(), window.sentinel.companionStatus(), renderGames()])
  .then(([snapshot, companion]) => {
    setAccount(snapshot?.session, snapshot?.features || []);
    setCompanion(companion);
    setWowCheckpoint({ state: 'STOPPED' });
    setOverlayStatus({ visible: false, count: 0 });
  })
  .catch(error => showError(companionStatus, error));
