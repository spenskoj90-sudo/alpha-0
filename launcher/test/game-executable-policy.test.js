'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { isConfiguredWindowsPath, isSelectableExecutable, gameLaunchState } = require('../game-executable-policy');
const win = { id: 'diablo-2-pc', platform: 'windows' };
const android = { id: 'diablo-immortal-android', platform: 'android' };

test('Windows native selection accepts local absolute .exe paths with spaces and case-insensitive extension', () => {
  for (const p of ['C:\\Program Files\\Games\\game.exe', 'D:\\Diablo II\\D2R.EXE', 'C:/Games/Diablo.exe']) {
    assert.equal(isSelectableExecutable(p), true, p);
  }
  for (const p of [null, '', 'game.exe', 'C:game.exe', '\\\\server\\share\\game.exe', 'https://bad.example/game.exe', 'C:\\Games\\game.bat', 'C:\\Games\\game.exe\n', ' C:\\Games\\game.exe', 'C:\\Games\\game.exe ']) {
    assert.equal(isSelectableExecutable(p), false, String(p));
  }
});

test('catalog readiness is fail-closed on missing, invalid, or inaccessible configured paths', () => {
  assert.equal(gameLaunchState(android, 'C:\\Games\\game.exe', () => { throw Error('should not inspect'); }), 'ANDROID_CLIENT');
  assert.equal(gameLaunchState(win, undefined, () => { throw Error('should not inspect'); }), 'NOT_CONFIGURED');
  assert.equal(gameLaunchState(win, 'game.exe', () => { throw Error('should not inspect'); }), 'INVALID_PATH');
  assert.equal(gameLaunchState(win, 'C:\\Games\\game.exe', () => { throw Error('missing'); }), 'FILE_MISSING');
  assert.equal(gameLaunchState(win, 'C:\\Games\\game.exe', () => ({isFile: () => false})), 'FILE_MISSING');
  assert.equal(gameLaunchState(win, 'C:\\Games\\game.exe', () => ({isFile: () => true})), 'READY');
});

test('pre-existing absolute non-exe paths retain former launch config compatibility', () => {
  assert.equal(isConfiguredWindowsPath('C:\\Games\\launch.cmd'), true);
  assert.equal(isSelectableExecutable('C:\\Games\\launch.cmd'), false);
  assert.equal(gameLaunchState(win, 'C:\\Games\\launch.cmd', () => ({isFile: () => true})), 'READY');
});
