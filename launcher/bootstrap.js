const smokeMode = process.env.SENTINEL_PACKAGED_HOST_SMOKE === '1';

if (smokeMode) {
  require('./package-smoke');
} else {
  const { app } = require('electron');
  // One process owns persistent cache/session/lifecycle mutable state.
  if (app.requestSingleInstanceLock()) require('./main');
  else app.quit();
}
