'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');
const start = source.indexOf('async function renderGames() {');
const end = source.indexOf('\nfunction stopVoiceTracks()', start);
assert.ok(start >= 0 && end > start, 'game card presenter is present');

function element(tag) {
  return {
    tag, children: [], attributes: {}, style: {}, hidden: false,
    append(...items) { this.children.push(...items); },
    appendChild(item) { this.children.push(item); },
    replaceChildren(...items) { this.children = [...items]; },
    setAttribute(name, value) { this.attributes[name] = value; },
    querySelector(selector) {
      if (!selector.startsWith('.')) return null;
      const className = selector.slice(1);
      const find = node => {
        if (String(node.className || '').split(/\s+/).includes(className)) return node;
        for (const child of node.children || []) {
          const match = find(child);
          if (match) return match;
        }
        return null;
      };
      return find(this);
    },
  };
}

function harness(catalog, launch, chooseExecutable = async () => ({ configured: false })) {
  const grid = element('div');
  const context = {
    window: { sentinel: { catalog: async () => catalog, launch, chooseExecutable },
      alert() { throw Error('native alert must not receive a host OS exception'); } },
    document: { createElement: element },
    ui: { t: key => key },
    $: id => id === 'grid' ? grid : null,
  };
  const render = vm.runInNewContext('(' + source.slice(start, end) + ')', context);
  return { render, grid };
}

const game = { id: 'diablo-2-pc', name: 'Diablo II', platform: 'windows', launchState: 'READY' };

test('launch card locks both controls until OS acknowledges and reports non-modal success', async () => {
  let complete;
  let calls = 0;
  const h = harness([game], () => {
    calls++;
    return new Promise(resolve => { complete = resolve; });
  });
  await h.render();
  const card = h.grid.children[0];
  const actions = card.children[2];
  const [launchButton, picker] = actions.children;
  const feedback = card.children[4];
  assert.equal(feedback.hidden, true);
  const pending = launchButton.onclick();
  assert.equal(launchButton.disabled, true);
  assert.equal(picker.disabled, true);
  assert.equal(feedback.textContent, 'GAME LAUNCH REQUESTED');
  assert.equal(feedback.attributes['aria-live'], 'polite');
  await launchButton.onclick();
  assert.equal(calls, 1, 'double activation must not submit another IPC request');
  complete(true);
  await pending;
  assert.equal(launchButton.disabled, false);
  assert.equal(picker.disabled, false);
  assert.equal(feedback.textContent, 'GAME PROCESS STARTED');
  assert.equal(feedback.attributes['data-i18n'], 'GAME PROCESS STARTED');
});

test('OS launch failure displays bounded localized error without disclosing host paths', async () => {
  const h = harness([game], async () => { throw Error('C:\\Users\\Private\\Game.exe: Access denied'); });
  await h.render();
  const card = h.grid.children[0];
  const actions = card.children[2];
  await actions.children[0].onclick();
  assert.equal(card.children[4].textContent, 'GAME LAUNCH FAILED');
  assert.equal(card.children[4].className, 'status game-launch-status err');
  assert.equal(actions.children[0].disabled, false);
  assert.equal(actions.children[1].disabled, false);
});

test('Android catalog card never exposes a PC launch handler', async () => {
  const h = harness([{ id: 'diablo-immortal-android', name: 'Diablo Immortal', platform: 'android' }],
    () => { throw Error('must not launch'); });
  await h.render();
  const button = h.grid.children[0].children[2];
  assert.equal(button.disabled, true);
  assert.equal(button.onclick, undefined);
});
