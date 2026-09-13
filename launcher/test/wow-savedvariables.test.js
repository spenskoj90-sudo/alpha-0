'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  WowCheckpointBridge,
  WowObservationQueue,
  discoverSentinelSavedVariables,
  normalizeSnapshot,
  parseSavedVariables,
} = require('../wow-savedvariables');
const { wowObservationEnvelope } = require('../companion-worker');

function savedVariables(sequence = 7) {
  return `SentinelDB = {\n  ["snapshot_sequence"] = ${sequence},\n  ["snapshot"] = {\n    ["schema_version"] = 1,\n    ["sequence"] = ${sequence},\n    ["observed_at_epoch"] = 1789290000,\n    ["patch_profile"] = "wotlk-3.3.5a",\n    ["server_profile"] = "unknown",\n    ["realm_id"] = "Example Realm",\n    ["latency_ms"] = 84,\n    ["addon_connected"] = true,\n    ["combat_state"] = "IDLE",\n  },\n}\n`;
}

test('strict SavedVariables parser extracts only passive Sentinel checkpoint data', () => {
  const parsed = parseSavedVariables(savedVariables());
  const observation = normalizeSnapshot(parsed);
  assert.equal(observation.patch_profile, 'wotlk-3.3.5a');
  assert.equal(observation.realm_id, 'Example Realm');
  assert.equal(observation.latency_ms, 84);
  assert.equal(observation.addon_connected, true);
  assert.equal(observation.launcher_associated, true);
  assert.equal(observation.data_quality, 'LOW');
  assert.match(observation.event_id, /^wow-checkpoint-[0-9a-f]{32}$/);
  assert.equal(JSON.stringify(observation).includes('player'), false);
});

test('SavedVariables parser rejects executable Lua instead of evaluating it', () => {
  assert.throws(
    () => parseSavedVariables('SentinelDB = os.execute("calc")'),
    /SAVEDVARIABLES_UNSUPPORTED_VALUE/,
  );
  assert.throws(
    () => parseSavedVariables('SentinelDB = { snapshot = function() end }'),
    /SAVEDVARIABLES_UNSUPPORTED_VALUE/,
  );
});

test('durable observation queue is bounded, deduplicated and acknowledged FIFO', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-wow-queue-'));
  const filePath = path.join(dir, 'queue.json');
  const queue = new WowObservationQueue({ filePath, maxItems: 2 });
  const a = { event_id: 'a' };
  const b = { event_id: 'b' };
  const c = { event_id: 'c' };
  assert.equal(queue.enqueue(a), true);
  assert.equal(queue.enqueue(a), false);
  assert.equal(queue.enqueue(b), true);
  assert.equal(queue.enqueue(c), true);
  assert.equal(queue.depth, 2);
  assert.equal(queue.dropped, 1);
  assert.equal(queue.peek().event_id, 'b');
  assert.equal(queue.acknowledge('c'), false);
  assert.equal(queue.acknowledge('b'), true);
  assert.equal(queue.peek().event_id, 'c');
  const reloaded = new WowObservationQueue({ filePath, maxItems: 2 });
  assert.equal(reloaded.peek().event_id, 'c');
});

test('checkpoint bridge keeps data queued until Companion is active and ACKed', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-wow-bridge-'));
  const source = path.join(dir, 'Sentinel.lua');
  fs.writeFileSync(source, savedVariables(9));
  const queue = new WowObservationQueue({ filePath: path.join(dir, 'queue.json') });
  const sent = [];
  const statuses = [];
  const bridge = new WowCheckpointBridge({
    queue,
    resolvePath: () => source,
    sendObservation: observation => { sent.push(observation); return true; },
    onStatus: status => statuses.push(status),
    setIntervalImpl: () => 1,
    clearIntervalImpl: () => {},
  });
  bridge.start();
  assert.equal(queue.depth, 1);
  assert.equal(sent.length, 0);
  bridge.onCompanionStatus({ state: 'ACTIVE' });
  assert.equal(sent.length, 1);
  assert.equal(queue.depth, 1);
  const eventId = sent[0].event_id;
  assert.equal(bridge.acknowledge(eventId, true, 'PASSIVE_CHECKPOINT_ACCEPTED'), true);
  assert.equal(queue.depth, 0);
  assert.equal(statuses.some(status => status.state === 'DELIVERED'), true);
  bridge.stop();
});

test('SavedVariables discovery is constrained to configured WoW root or trusted override', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-wow-discovery-'));
  const executable = path.join(dir, 'Wow.exe');
  fs.writeFileSync(executable, '');
  const saved = path.join(dir, 'WTF', 'Account', 'ACCOUNT1', 'SavedVariables', 'Sentinel.lua');
  fs.mkdirSync(path.dirname(saved), { recursive: true });
  fs.writeFileSync(saved, savedVariables());
  assert.equal(discoverSentinelSavedVariables(executable), saved);
  assert.equal(discoverSentinelSavedVariables(executable, path.join(dir, 'Other.lua')), null);
});

test('Companion observation envelope is passive background transport', () => {
  const observation = normalizeSnapshot(parseSavedVariables(savedVariables()));
  const envelope = wowObservationEnvelope(observation, 11);
  assert.equal(envelope.message_type, 'WOW_OBSERVATION');
  assert.equal(envelope.latency_class, 'BACKGROUND');
  assert.equal(envelope.sequence, 11);
  assert.equal(envelope.payload.event_id, observation.event_id);
});

test('Classic and Retail addon sources persist only the bounded passive snapshot contract', () => {
  const repoRoot = path.resolve(__dirname, '..', '..');
  for (const variant of ['classic', 'retail']) {
    const source = fs.readFileSync(path.join(repoRoot, 'wow-addon', variant, 'Sentinel.lua'), 'utf8');
    assert.match(source, /SentinelDB\.snapshot\s*=\s*\{/);
    for (const field of ['schema_version', 'sequence', 'observed_at_epoch', 'patch_profile', 'server_profile', 'realm_id', 'latency_ms', 'addon_connected', 'combat_state']) {
      assert.match(source, new RegExp(`${field}\\s*=`));
    }
    assert.doesNotMatch(source, /io\.|require\(|socket|SendChatMessage\(|CastSpell|RunMacro/);
  }
});
