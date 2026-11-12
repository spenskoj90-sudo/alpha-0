'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { saveGameConfigFile } = require('../game-config-store');

function directory() { return fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-game-config-')); }

test('replaces existing game paths without truncation and leaves no temporary files', t => {
  const root = directory();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const file = path.join(root, 'games.json');
  fs.writeFileSync(file, '{"world-of-warcraft":"C:\\old.exe"}');
  const payload = { 'world-of-warcraft': 'D:\\Games\\Wow.exe', 'diablo-2-pc': 'D:\\Games\\Diablo II.exe' };
  saveGameConfigFile(file, payload);
  assert.deepEqual(JSON.parse(fs.readFileSync(file, 'utf8')), payload);
  assert.deepEqual(fs.readdirSync(root), ['games.json']);
  if (process.platform !== 'win32') assert.equal(fs.statSync(file).mode & 0o777, 0o600);
});

test('rename failure keeps previous settings and removes complete staged file', t => {
  const root = directory();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const file = path.join(root, 'games.json');
  const original = '{"world-of-warcraft":"old"}';
  fs.writeFileSync(file, original);
  const io = { writeFileSync: fs.writeFileSync, unlinkSync: fs.unlinkSync,
    renameSync() { throw Error('rename failed'); } };
  assert.throws(() => saveGameConfigFile(file, { 'world-of-warcraft': 'new' }, io, () => 'abc'), /rename failed/);
  assert.equal(fs.readFileSync(file, 'utf8'), original);
  assert.deepEqual(fs.readdirSync(root), ['games.json']);
});

test('partial temporary write failure never overwrites existing config', t => {
  const root = directory();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const file = path.join(root, 'games.json');
  const original = '{"diablo-2-pc":"old"}';
  fs.writeFileSync(file, original);
  const io = { unlinkSync: fs.unlinkSync, renameSync: fs.renameSync,
    writeFileSync(temp, _data, options) { fs.writeFileSync(temp, 'partial', options); throw Error('disk full'); } };
  assert.throws(() => saveGameConfigFile(file, { 'diablo-2-pc': 'new' }, io, () => 'xyz'), /disk full/);
  assert.equal(fs.readFileSync(file, 'utf8'), original);
  assert.deepEqual(fs.readdirSync(root), ['games.json']);
});
