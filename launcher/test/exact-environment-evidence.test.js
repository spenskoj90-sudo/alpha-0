'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { CompanionProcessManager } = require('../companion-process');
const { handshakeEvidence } = require('../companion-worker');
const {
  ExactEnvironmentEvidenceRecorder,
  deriveCapabilityClaims,
  getProcessExactEnvironmentEvidenceRecorder,
  resetProcessExactEnvironmentEvidenceRecorderForTests,
} = require('../exact-environment-evidence');

const SOURCE_SHA = 'a'.repeat(40);
const CONNECTION_ID = '11111111-1111-4111-8111-111111111111';

function packagedProvenance() {
  return {
    schema: 'sentinel.packaged-companion-runtime.v1',
    sourceSha: SOURCE_SHA,
    sourceBound: true,
    target: 'win32-x64',
    packageVersion: '0.2.0',
    electronVersion: '37.2.0',
    signed: false,
    provenanceFileSha256: 'b'.repeat(64),
  };
}

function health() {
  return {
    healthKind: 'runtime',
    connectionId: CONNECTION_ID,
    heartbeatMessageId: '22222222-2222-4222-8222-222222222222',
    mode: 'ACTIVE',
    reconnectAttempts: 0,
    queueDepth: 0,
    droppedEvents: 0,
    killSwitchActive: false,
    peerAuthenticated: true,
    rttMs: 8,
    rtt: { count: 1, minimumMs: 8, maximumMs: 8, averageMs: 8, p95Ms: 8 },
  };
}

function acceptedCheckpoint(sequence, digestChar) {
  const eventId = `wow-checkpoint-${sequence}`;
  const observedAt = new Date(Date.UTC(2026, 8, 14, 9, 30, sequence)).toISOString();
  return {
    checkpointSha256: digestChar.repeat(64),
    checkpointSizeBytes: 2048 + sequence,
    pathFingerprintSha256: 'f'.repeat(64),
    capturedAt: observedAt,
    observation: {
      event_id: eventId,
      observed_at: observedAt,
      sequence,
      patch_profile: 'wotlk-3.3.5a',
      server_profile: 'private',
      realm_id: 'Example Realm',
      latency_ms: 84,
      addon_connected: true,
      launcher_associated: true,
      combat_state: 'IDLE',
      data_quality: 'LOW',
      provenance: ['sentinel-addon-savedvariables', 'sentinel-launcher-checkpoint'],
    },
    coreAck: {
      eventId,
      accepted: true,
      reason: 'PASSIVE_CHECKPOINT_ACCEPTED',
      acknowledgedAt: new Date(Date.UTC(2026, 8, 14, 9, 31, sequence)).toISOString(),
    },
  };
}

function fixedClock() {
  let tick = 0;
  return () => new Date(Date.UTC(2026, 8, 14, 9, 29, tick++));
}

test('recorder writes no bundle until handshake, health and two Core-accepted checkpoints exist', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-l3-recorder-'));
  const outputPath = path.join(dir, 'l3-evidence.json');
  const recorder = new ExactEnvironmentEvidenceRecorder({
    outputPath,
    environmentId: 'wotlk-private-lab-a',
    packagedProvenance: packagedProvenance(),
    now: fixedClock(),
  });

  assert.equal(recorder.acceptHandshake(handshakeEvidence(new Date('2026-09-14T09:29:10Z'))), true);
  assert.equal(recorder.acceptHealth(health()), true);
  assert.equal(recorder.acceptCheckpoint(acceptedCheckpoint(1, 'c')), true);
  assert.equal(fs.existsSync(outputPath), false);

  assert.equal(recorder.acceptCheckpoint(acceptedCheckpoint(2, 'd')), true);
  assert.equal(fs.existsSync(outputPath), true);
  const payload = JSON.parse(fs.readFileSync(outputPath, 'utf8'));
  assert.equal(payload.execution_mode, 'live-exact-environment');
  assert.equal(payload.source_sha, SOURCE_SHA);
  assert.equal(payload.adapter_identity.environment_id, 'wotlk-private-lab-a');
  assert.equal(payload.adapter_identity.server_profile, 'private');
  assert.equal(payload.checkpoints.length, 2);
  assert.equal(payload.health_samples.length, 1);
  assert.deepEqual(payload.capability_claims, [
    'wow.account_entitlement',
    'wow.addon_status',
    'wow.identity',
    'wow.latency',
    'wow.launcher_association',
    'wow.passive_telemetry',
    'wow.patch_profile',
    'wow.realm_profile',
  ]);
  assert.equal(JSON.stringify(payload).includes('access-token'), false);
  assert.equal(recorder.snapshot().state, 'BUNDLE_READY');
});

test('unknown or drifting environment identity never becomes a ready bundle', () => {
  const first = acceptedCheckpoint(1, 'c');
  first.observation.server_profile = 'unknown';
  const second = acceptedCheckpoint(2, 'd');
  second.observation.server_profile = 'unknown';
  assert.deepEqual(deriveCapabilityClaims([
    { observation: first.observation },
    { observation: second.observation },
  ]), []);

  const drift = acceptedCheckpoint(2, 'd');
  drift.observation.realm_id = 'Other Realm';
  assert.deepEqual(deriveCapabilityClaims([
    { observation: acceptedCheckpoint(1, 'c').observation },
    { observation: drift.observation },
  ]), []);
});

test('recorder rejects unbound package provenance and Companion connection drift', () => {
  assert.throws(
    () => new ExactEnvironmentEvidenceRecorder({
      outputPath: path.join(os.tmpdir(), 'should-not-exist.json'),
      environmentId: 'env-a',
      packagedProvenance: { ...packagedProvenance(), sourceBound: false },
    }),
    /SOURCE_BOUND_PACKAGE_REQUIRED/,
  );

  const recorder = new ExactEnvironmentEvidenceRecorder({
    outputPath: path.join(os.tmpdir(), `sentinel-${Date.now()}-l3.json`),
    environmentId: 'env-a',
    packagedProvenance: packagedProvenance(),
  });
  assert.equal(recorder.acceptHealth(health()), true);
  assert.equal(recorder.acceptHealth({ ...health(), connectionId: '33333333-3333-4333-8333-333333333333' }), false);
  assert.equal(recorder.snapshot().reason, 'COMPANION_CONNECTION_CHANGED');
});

class FakeChild extends EventEmitter {
  constructor() { super(); this.connected = true; this.killed = false; this.messages = []; }
  send(message) { this.messages.push(message); }
  kill() { this.killed = true; this.connected = false; }
}

test('Companion process feeds only sanitized handshake and health to the evidence recorder', async () => {
  const child = new FakeChild();
  const accepted = { handshakes: [], health: [] };
  const evidenceRecorder = {
    acceptHandshake: value => accepted.handshakes.push(value),
    acceptHealth: value => accepted.health.push(value),
  };
  const manager = new CompanionProcessManager({ forkImpl: () => child, evidenceRecorder });
  manager.start({ coreUrl: 'http://127.0.0.1:8080', sessionToken: 'access-token-0123456789' });
  child.emit('message', { type: 'handshake-evidence', handshake: handshakeEvidence(new Date('2026-09-14T09:30:00Z')) });
  child.emit('message', { type: 'runtime-health', health: health() });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(accepted.handshakes.length, 1);
  assert.equal(accepted.health.length, 1);
  assert.equal(accepted.handshakes[0].capabilityProfile, 'wow.passive.v1');
  assert.equal(accepted.health[0].peerAuthenticated, true);
  manager.stop('TEST_COMPLETE');
});

test('process recorder is disabled by default and rejects SavedVariables override for L3 capture', () => {
  resetProcessExactEnvironmentEvidenceRecorderForTests();
  assert.equal(getProcessExactEnvironmentEvidenceRecorder({ env: {} }), null);

  resetProcessExactEnvironmentEvidenceRecorderForTests();
  assert.throws(
    () => getProcessExactEnvironmentEvidenceRecorder({
      env: {
        SENTINEL_L3_EVIDENCE_OUTPUT: path.join(os.tmpdir(), 'l3.json'),
        SENTINEL_L3_ENVIRONMENT_ID: 'env-a',
        SENTINEL_WOW_SAVEDVARIABLES_PATH: path.join(os.tmpdir(), 'Sentinel.lua'),
      },
    }),
    /REJECTS_SAVEDVARIABLES_OVERRIDE/,
  );
  resetProcessExactEnvironmentEvidenceRecorderForTests();
});
