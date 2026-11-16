'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createGameLaunchGate } = require('../game-launch-gate');

test('blocks concurrent launch of same game until OS acknowledges spawn', async () => {
  let release;
  let count = 0;
  const gate = createGameLaunchGate(async () => {
    count += 1;
    return new Promise(resolve => { release = resolve; });
  });
  const first = gate('diablo-2-pc', 'C:\\Games\\D2.exe');
  await assert.rejects(gate('diablo-2-pc', 'C:\\Games\\D2.exe'), { message: 'GAME_LAUNCH_IN_PROGRESS' });
  assert.equal(count, 1);
  release(true);
  assert.equal(await first, true);
  const second = gate('diablo-2-pc', 'C:\\Games\\D2.exe');
  release(true);
  assert.equal(await second, true);
  assert.equal(count, 2);
});

test('independent games can launch concurrently', async () => {
  const callbacks = new Map();
  const gate = createGameLaunchGate(executable => new Promise(resolve => callbacks.set(executable, resolve)));
  const a = gate('diablo-2-pc', 'A');
  const b = gate('diablo-4-pc', 'B');
  assert.equal(callbacks.size, 2);
  callbacks.get('A')(true);
  callbacks.get('B')(true);
  assert.equal(await a, true);
  assert.equal(await b, true);
});

test('failed spawn releases per-game lease for retry', async () => {
  let count = 0;
  const gate = createGameLaunchGate(async () => {
    count += 1;
    if (count === 1) throw new Error('GAME_PROCESS_LAUNCH_FAILED');
    return true;
  });
  await assert.rejects(gate('diablo-2-pc', 'C:\\Games\\D2.exe'), { message: 'GAME_PROCESS_LAUNCH_FAILED' });
  assert.equal(await gate('diablo-2-pc', 'C:\\Games\\D2.exe'), true);
  assert.equal(count, 2);
});
