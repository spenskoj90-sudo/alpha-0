'use strict';

const { spawn } = require('node:child_process');

/** Confirm OS process creation before reporting successful launch to the UI. */
function launchGameExecutable(executable, spawnProcess = spawn) {
  return new Promise((resolve, reject) => {
    let child;
    try {
      child = spawnProcess(executable, [], { detached: true, stdio: 'ignore', windowsHide: false, shell: false });
    } catch {
      reject(new Error('GAME_PROCESS_LAUNCH_FAILED'));
      return;
    }
    if (!child || typeof child.on !== 'function' ||
        typeof child.once !== 'function' || typeof child.unref !== 'function') {
      reject(new Error('GAME_PROCESS_LAUNCH_FAILED'));
      return;
    }
    let settled = false;
    const fail = () => {
      if (settled) return;
      settled = true;
      reject(new Error('GAME_PROCESS_LAUNCH_FAILED'));
    };
    // Retain a listener after spawn: an eventual child error must never crash Electron.
    child.on('error', fail);
    child.once('spawn', () => {
      if (settled) return;
      try { child.unref(); } catch { fail(); return; }
      settled = true;
      resolve(true);
    });
  });
}

module.exports = { launchGameExecutable };
