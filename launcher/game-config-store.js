'use strict';

const fs = require('node:fs');
const { randomBytes } = require('node:crypto');

/** Replace game settings only after a complete, private temp file is written. */
function saveGameConfigFile(filePath, config, io = fs, nonce = () => randomBytes(8).toString('hex')) {
  const temporaryPath = filePath + '.' + process.pid + '.' + nonce() + '.tmp';
  try {
    io.writeFileSync(temporaryPath, JSON.stringify(config, null, 2), {
      encoding: 'utf8', mode: 0o600, flag: 'wx',
    });
    // Same-directory rename protects the previous settings on failed writes.
    io.renameSync(temporaryPath, filePath);
  } catch (error) {
    try { io.unlinkSync(temporaryPath); } catch { /* Temp file may not exist. */ }
    throw error;
  }
}

module.exports = { saveGameConfigFile };
