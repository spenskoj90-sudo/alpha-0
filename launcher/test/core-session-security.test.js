'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { normalizeCoreUrl } = require('../core-session');

test('Core URL accepts HTTPS remote origins', () => {
  assert.equal(normalizeCoreUrl('https://core.example.test/'), 'https://core.example.test');
});

test('Core URL permits HTTP only on loopback', () => {
  assert.equal(normalizeCoreUrl('http://127.0.0.1:8080/'), 'http://127.0.0.1:8080');
  assert.equal(normalizeCoreUrl('http://localhost:8080/'), 'http://localhost:8080');
  assert.equal(normalizeCoreUrl('http://[::1]:8080/'), 'http://[::1]:8080');
  assert.throws(() => normalizeCoreUrl('http://core.example.test'), /INSECURE_CORE_URL/);
});

test('Core URL rejects credentials, query parameters and fragments', () => {
  assert.throws(() => normalizeCoreUrl('https://user:pass@core.example.test'), /INVALID_CORE_URL/);
  assert.throws(() => normalizeCoreUrl('https://core.example.test?token=x'), /INVALID_CORE_URL/);
  assert.throws(() => normalizeCoreUrl('https://core.example.test/#x'), /INVALID_CORE_URL/);
});
