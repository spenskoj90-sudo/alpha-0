'use strict';

const path = require('node:path');

/** A configured local path is not proof of publisher identity or game authority. */
function isConfiguredWindowsPath(filePath) {
  return typeof filePath === 'string' &&
    filePath.length >= 4 && filePath.length <= 4096 && filePath === filePath.trim() &&
    !/[\x00-\x1f\x7f]/.test(filePath) && path.win32.isAbsolute(filePath);
}

/** The native file picker accepts only .exe; existing configured file paths remain readable. */
function isSelectableExecutable(filePath) {
  return isConfiguredWindowsPath(filePath) && /^[A-Za-z]:[\\/]/.test(filePath) &&
    path.win32.extname(filePath).toLowerCase() === '.exe';
}

function gameLaunchState(game, configuredPath, statFile) {
  if (!game || game.platform !== 'windows') return 'ANDROID_CLIENT';
  if (configuredPath === undefined || configuredPath === null || configuredPath === '') return 'NOT_CONFIGURED';
  if (!isConfiguredWindowsPath(configuredPath)) return 'INVALID_PATH';
  try {
    return statFile(configuredPath)?.isFile() === true ? 'READY' : 'FILE_MISSING';
  } catch {
    return 'FILE_MISSING';
  }
}

module.exports = { isConfiguredWindowsPath, isSelectableExecutable, gameLaunchState };
