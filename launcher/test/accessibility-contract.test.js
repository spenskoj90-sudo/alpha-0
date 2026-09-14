'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const index = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

test('launcher exposes keyboard and landmark accessibility contract', () => {
  assert.match(index, /<html lang="en">/);
  assert.match(index, /class="skip-link" href="#main-content"/);
  assert.match(index, /<main id="main-content" tabindex="-1">/);
  assert.match(index, /:focus-visible\{outline:3px solid #4ca3ff/);
  assert.match(index, /@media\(forced-colors:active\)/);
});

test('launcher runtime state is announced through bounded live regions', () => {
  for (const id of ['account-status', 'companion-status', 'wow-checkpoint-status', 'voice-status', 'voice-result']) {
    assert.match(
      index,
      new RegExp(`id="${id}"[^>]*role="status"[^>]*aria-live="polite"[^>]*aria-atomic="true"`),
      `${id} must remain a polite atomic live region`,
    );
  }
});

test('launcher form controls retain explicit labels and semantic native controls', () => {
  for (const id of ['core-url', 'email', 'password', 'voice-consent', 'voice-locale']) {
    assert.match(index, new RegExp(`<label[^>]*for="${id}"|<label[^>]*for="${id}"`, 'i'));
  }
  assert.match(index, /<button id="login"/);
  assert.match(index, /<button id="voice-ptt"/);
});
