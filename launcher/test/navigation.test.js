'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function openNavigation(hash) {
  const events = {};
  const links = ['#overview', '#account', '#voice'].map(href => ({
    href, attributes: {},
    getAttribute(name) { return name === 'href' ? this.href : this.attributes[name]; },
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; },
  }));
  const window = { location: { hash }, addEventListener(name, handler) { events[name] = handler; } };
  const document = { getElementById() { return null; }, querySelectorAll() { return links; } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'accessibility-runtime.js'), 'utf8'), { window, document });
  return { links, window, events };
}

test('Companion selects the initial section and moves selection with hash navigation', () => {
  const { links, window, events } = openNavigation('');
  assert.deepEqual(links.map(link => link.attributes['aria-current']), ['location', undefined, undefined]);
  window.location.hash = '#voice';
  events.hashchange();
  assert.deepEqual(links.map(link => link.attributes['aria-current']), [undefined, undefined, 'location']);
  window.location.hash = '#account';
  events.hashchange();
  assert.deepEqual(links.map(link => link.attributes['aria-current']), [undefined, 'location', undefined]);
});

test('Companion restores a deep section and never marks an unknown target as current', () => {
  const { links, window, events } = openNavigation('#voice');
  assert.equal(links[2].attributes['aria-current'], 'location');
  window.location.hash = '#missing';
  events.hashchange();
  assert.equal(links.some(link => link.attributes['aria-current']), false);
});
