'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { launchGameExecutable } = require('../game-process-launch');

function fakeChild(unref = () => {}) {
  const child = new EventEmitter();
  child.unref = unref;
  return child;
}

test('launch acknowledges only spawn success with detached non-shell configuration', async () => {
  let unrefCount = 0;
  const child = fakeChild(() => { unrefCount += 1; });
  const executable = 'C:\\Games\\Game.exe';
  let argumentsSeen;
  const result = launchGameExecutable(executable, (...args) => {
    argumentsSeen = args;
    return child;
  });
  assert.deepEqual(argumentsSeen, [executable, [], { detached: true, stdio: 'ignore', windowsHide: false, shell: false }]);
  child.emit('spawn');
  assert.equal(await result, true);
  assert.equal(unrefCount, 1);
  assert.doesNotThrow(() => child.emit('error', new Error('late OS error')));
  assert.equal(unrefCount, 1);
});

test('failed OS spawn rejects without leaking raw error details or causing unhandled event', async () => {
  const child = fakeChild();
  const result = launchGameExecutable('C:\\Games\\Game.exe', () => child);
  assert.doesNotThrow(() => child.emit('error', new Error('Sensitive OS path')));
  await assert.rejects(result, { message: 'GAME_PROCESS_LAUNCH_FAILED' });
  child.emit('spawn');
});

test('synchronous spawn failures and invalid child objects fail closed', async () => {
  await assert.rejects(launchGameExecutable('C:\\Games\\Game.exe', () => { throw new Error('sensitive'); }), { message: 'GAME_PROCESS_LAUNCH_FAILED' });
  await assert.rejects(launchGameExecutable('C:\\Games\\Game.exe', () => null), { message: 'GAME_PROCESS_LAUNCH_FAILED' });
});

test('failure to detach is never reported as a successful launch', async () => {
  const child = fakeChild(() => { throw new Error('detach failed'); });
  const result = launchGameExecutable('C:\\Games\\Game.exe', () => child);
  child.emit('spawn');
  await assert.rejects(result, { message: 'GAME_PROCESS_LAUNCH_FAILED' });
});
