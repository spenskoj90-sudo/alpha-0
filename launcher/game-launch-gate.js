'use strict';

/** Reject simultaneous launch requests for one game until OS spawn is acknowledged. */
function createGameLaunchGate(launch) {
  const pending = new Set();
  return async (gameId, executable) => {
    if (pending.has(gameId)) throw new Error('GAME_LAUNCH_IN_PROGRESS');
    pending.add(gameId);
    try {
      return await launch(executable);
    } finally {
      pending.delete(gameId);
    }
  };
}

module.exports = { createGameLaunchGate };
