'use strict';

const path = require('node:path');
const { pathToFileURL } = require('node:url');

/**
 * Bind privileged IPC and page navigation to a single packaged document.
 * In-page fragment links are allowed. Query strings, other files and frames
 * never receive main-process privileges.
 */
function documentUrl(directory, filename) {
  return pathToFileURL(path.join(directory, filename)).href;
}

function isLocalDocument(url, expectedDocument) {
  if (typeof url !== 'string' || typeof expectedDocument !== 'string') return false;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'file:' || parsed.search !== '') return false;
    parsed.hash = '';
    return parsed.href === expectedDocument;
  } catch { return false; }
}

function assertMainFrameRequest(event, win, expectedDocument) {
  const contents = win?.webContents;
  if (!contents || win.isDestroyed() ||
      event?.sender !== contents || event?.senderFrame !== contents.mainFrame ||
      !isLocalDocument(event?.senderFrame?.url, expectedDocument) ||
      !isLocalDocument(contents.getURL(), expectedDocument)) {
    throw new Error('UNTRUSTED_RENDERER');
  }
}

/** Electron 44 exposes navigation details.url, while legacy arguments may
 * carry a positional URL. Unknown/untrusted navigation always fails closed. */
function restrictAppWindowNavigation(contents, expectedDocument) {
  contents.setWindowOpenHandler(() => ({ action: 'deny' }));
  contents.on('will-navigate', (event, details) => {
    const url = typeof details === 'string' ? details : details?.url ?? event?.url;
    if (!isLocalDocument(url, expectedDocument)) event.preventDefault();
  });
  contents.on('will-frame-navigate', (event, details) => {
    if (details?.isMainFrame !== true ||
        !isLocalDocument(details?.url, expectedDocument)) event.preventDefault();
  });
}

module.exports = { documentUrl, isLocalDocument, assertMainFrameRequest, restrictAppWindowNavigation };
