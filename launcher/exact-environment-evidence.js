'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { readPackagedBuildProvenance } = require('./packaged-runtime');

const ENVIRONMENT_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const GIT_SHA_RE = /^[0-9a-f]{40}$/;
const MAX_HEALTH_SAMPLES = 64;
const MAX_CHECKPOINTS = 64;
const EXPECTED_HANDSHAKE = Object.freeze({
  protocolVersion: '1.0',
  ugsSchemaVersion: '1.0',
  adapterContractVersion: '1.0',
  coreProtocolVersion: '1.0',
  capabilityProfile: 'wow.passive.v1',
});
let processRecorderInitialized = false;
let processRecorder = null;

function isoNow(now) {
  const value = now();
  if (!(value instanceof Date) || !Number.isFinite(value.getTime())) throw new Error('L3_EVIDENCE_CLOCK_INVALID');
  return value.toISOString();
}

function atomicWriteJson(filePath, payload, fsImpl = fs) {
  if (!path.isAbsolute(filePath)) throw new Error('L3_EVIDENCE_OUTPUT_MUST_BE_ABSOLUTE');
  const encoded = `${JSON.stringify(payload, null, 2)}\n`;
  if (Buffer.byteLength(encoded, 'utf8') > 2 * 1024 * 1024) throw new Error('L3_EVIDENCE_OUTPUT_TOO_LARGE');
  const directory = path.dirname(filePath);
  fsImpl.mkdirSync(directory, { recursive: true });
  const temp = `${filePath}.tmp`;
  fsImpl.writeFileSync(temp, encoded, { encoding: 'utf8', mode: 0o600 });
  fsImpl.renameSync(temp, filePath);
  try { fsImpl.chmodSync(filePath, 0o600); } catch {}
}

function normalizePackagedProvenance(value) {
  if (!value || value.schema !== 'sentinel.packaged-companion-runtime.v1') throw new Error('L3_PACKAGED_PROVENANCE_REQUIRED');
  if (!value.sourceBound || !GIT_SHA_RE.test(String(value.sourceSha || ''))) throw new Error('L3_SOURCE_BOUND_PACKAGE_REQUIRED');
  if (value.target !== 'win32-x64') throw new Error('L3_WINDOWS_PACKAGE_REQUIRED');
  if (typeof value.packageVersion !== 'string' || !value.packageVersion) throw new Error('L3_PACKAGE_VERSION_REQUIRED');
  if (typeof value.electronVersion !== 'string' || !value.electronVersion) throw new Error('L3_ELECTRON_VERSION_REQUIRED');
  if (!/^[0-9a-f]{64}$/.test(String(value.provenanceFileSha256 || ''))) throw new Error('L3_PROVENANCE_DIGEST_REQUIRED');
  return Object.freeze({
    schema: value.schema,
    source_sha: value.sourceSha,
    target: value.target,
    package_version: value.packageVersion,
    electron_version: value.electronVersion,
    signed: value.signed === true,
    provenance_file_sha256: value.provenanceFileSha256,
  });
}

function normalizeHandshake(value) {
  if (!value || value.accepted !== true || value.mode !== 'ACTIVE') return null;
  for (const [key, expected] of Object.entries(EXPECTED_HANDSHAKE)) {
    if (value[key] !== expected) return null;
  }
  const acceptedAt = new Date(value.acceptedAt);
  if (!Number.isFinite(acceptedAt.getTime())) return null;
  return Object.freeze({
    accepted_at: acceptedAt.toISOString(),
    accepted: true,
    mode: 'ACTIVE',
    protocol_version: value.protocolVersion,
    ugs_schema_version: value.ugsSchemaVersion,
    adapter_contract_version: value.adapterContractVersion,
    core_protocol_version: value.coreProtocolVersion,
    capability_profile: value.capabilityProfile,
  });
}

function normalizeHealth(value, capturedAt) {
  if (!value || value.healthKind !== 'runtime' || value.mode !== 'ACTIVE') return null;
  if (value.peerAuthenticated !== true || value.killSwitchActive === true) return null;
  if (typeof value.connectionId !== 'string' || !value.connectionId || value.connectionId.length > 128) return null;
  const integer = (item, max) => Number.isSafeInteger(item) && item >= 0 && item <= max ? item : null;
  const reconnectAttempts = integer(value.reconnectAttempts, 10_000);
  const queueDepth = integer(value.queueDepth, 4096);
  const droppedEvents = integer(value.droppedEvents, 1_000_000);
  const rttMs = Number.isFinite(value.rttMs) && value.rttMs >= 0 && value.rttMs <= 60_000 ? value.rttMs : null;
  if ([reconnectAttempts, queueDepth, droppedEvents, rttMs].some(item => item === null)) return null;
  return Object.freeze({
    captured_at: capturedAt,
    connection_id: value.connectionId,
    mode: 'ACTIVE',
    reconnect_attempts: reconnectAttempts,
    queue_depth: queueDepth,
    dropped_events: droppedEvents,
    kill_switch_active: false,
    peer_authenticated: true,
    rtt_ms: rttMs,
  });
}

function normalizeAcceptedCheckpoint(value) {
  if (!value || typeof value !== 'object') return null;
  if (!/^[0-9a-f]{64}$/.test(String(value.checkpointSha256 || ''))) return null;
  if (!/^[0-9a-f]{64}$/.test(String(value.pathFingerprintSha256 || ''))) return null;
  if (!Number.isSafeInteger(value.checkpointSizeBytes) || value.checkpointSizeBytes < 1 || value.checkpointSizeBytes > 256 * 1024) return null;
  if (!value.observation || typeof value.observation !== 'object') return null;
  if (!value.coreAck || value.coreAck.accepted !== true || value.coreAck.reason !== 'PASSIVE_CHECKPOINT_ACCEPTED') return null;
  if (value.coreAck.eventId !== value.observation.event_id) return null;
  const capturedAt = new Date(value.capturedAt);
  const acknowledgedAt = new Date(value.coreAck.acknowledgedAt);
  if (!Number.isFinite(capturedAt.getTime()) || !Number.isFinite(acknowledgedAt.getTime())) return null;
  return Object.freeze({
    checkpoint_sha256: value.checkpointSha256,
    checkpoint_size_bytes: value.checkpointSizeBytes,
    path_fingerprint_sha256: value.pathFingerprintSha256,
    captured_at: capturedAt.toISOString(),
    observation: { ...value.observation },
    core_ack: {
      event_id: value.coreAck.eventId,
      accepted: true,
      reason: value.coreAck.reason,
      acknowledged_at: acknowledgedAt.toISOString(),
    },
  });
}

function deriveCapabilityClaims(checkpoints) {
  if (checkpoints.length < 2) return [];
  const observations = checkpoints.map(item => item.observation);
  const patch = observations[0].patch_profile;
  const server = observations[0].server_profile;
  const realm = observations[0].realm_id;
  if (!patch || !server || server === 'unknown' || !realm) return [];
  if (observations.some(item => item.patch_profile !== patch || item.server_profile !== server || item.realm_id !== realm)) return [];
  if (observations.some(item => item.addon_connected !== true)) return [];
  const claims = [
    'wow.identity',
    'wow.patch_profile',
    'wow.realm_profile',
    'wow.addon_status',
    'wow.launcher_association',
    'wow.account_entitlement',
    'wow.passive_telemetry',
  ];
  if (observations.every(item => Number.isInteger(item.latency_ms) && item.latency_ms >= 0)) claims.push('wow.latency');
  return claims.sort();
}

class ExactEnvironmentEvidenceRecorder {
  constructor({ outputPath, environmentId, packagedProvenance, now = () => new Date(), fsImpl = fs } = {}) {
    if (!outputPath || !path.isAbsolute(outputPath)) throw new Error('L3_EVIDENCE_OUTPUT_MUST_BE_ABSOLUTE');
    if (!ENVIRONMENT_ID_RE.test(String(environmentId || ''))) throw new Error('L3_ENVIRONMENT_ID_INVALID');
    this.outputPath = outputPath;
    this.environmentId = environmentId;
    this.packagedHost = normalizePackagedProvenance(packagedProvenance);
    this.now = now;
    this.fs = fsImpl;
    this.startedAt = isoNow(now);
    this.evidenceId = `l3-${this.packagedHost.source_sha.slice(0, 12)}-${Date.parse(this.startedAt).toString(36)}`;
    this.handshake = null;
    this.healthSamples = [];
    this.checkpoints = [];
    this.lastStatus = Object.freeze({ state: 'CAPTURING', reason: 'AWAITING_LIVE_EVIDENCE' });
  }

  acceptHandshake(value) {
    const handshake = normalizeHandshake(value);
    if (!handshake) {
      this.lastStatus = Object.freeze({ state: 'BLOCKED', reason: 'HANDSHAKE_EVIDENCE_INVALID' });
      return false;
    }
    this.handshake = handshake;
    this.#maybeWrite();
    return true;
  }

  acceptHealth(value) {
    const health = normalizeHealth(value, isoNow(this.now));
    if (!health) return false;
    const last = this.healthSamples[this.healthSamples.length - 1];
    if (last && last.connection_id !== health.connection_id) {
      this.lastStatus = Object.freeze({ state: 'BLOCKED', reason: 'COMPANION_CONNECTION_CHANGED' });
      return false;
    }
    this.healthSamples.push(health);
    this.healthSamples = this.healthSamples.slice(-MAX_HEALTH_SAMPLES);
    this.#maybeWrite();
    return true;
  }

  acceptCheckpoint(value) {
    const checkpoint = normalizeAcceptedCheckpoint(value);
    if (!checkpoint) return false;
    if (this.checkpoints.some(item => item.observation.event_id === checkpoint.observation.event_id)) return false;
    this.checkpoints.push(checkpoint);
    this.checkpoints = this.checkpoints.slice(-MAX_CHECKPOINTS);
    this.#maybeWrite();
    return true;
  }

  snapshot() {
    return Object.freeze({
      ...this.lastStatus,
      evidenceId: this.evidenceId,
      sourceSha: this.packagedHost.source_sha,
      environmentId: this.environmentId,
      handshakeCaptured: Boolean(this.handshake),
      healthSamples: this.healthSamples.length,
      checkpoints: this.checkpoints.length,
      outputPath: this.outputPath,
    });
  }

  #maybeWrite() {
    if (!this.handshake || this.healthSamples.length < 1 || this.checkpoints.length < 2) return false;
    const claims = deriveCapabilityClaims(this.checkpoints);
    if (claims.length < 1) {
      this.lastStatus = Object.freeze({ state: 'BLOCKED', reason: 'EXACT_ENVIRONMENT_IDENTITY_INCOMPLETE' });
      return false;
    }
    const first = this.checkpoints[0].observation;
    const bundle = {
      schema_version: '1.0',
      evidence_id: this.evidenceId,
      execution_mode: 'live-exact-environment',
      source_sha: this.packagedHost.source_sha,
      started_at: this.startedAt,
      completed_at: isoNow(this.now),
      adapter_identity: {
        adapter_id: 'wow-conservative',
        adapter_version: '1.0',
        game_id: 'world-of-warcraft',
        client_family: String(first.patch_profile).split('-')[0],
        client_version: first.patch_profile,
        server_profile: first.server_profile,
        environment_id: this.environmentId,
        capability_profile_version: '1.0',
      },
      packaged_host: this.packagedHost,
      handshake: this.handshake,
      health_samples: this.healthSamples,
      checkpoints: this.checkpoints,
      capability_claims: claims,
    };
    atomicWriteJson(this.outputPath, bundle, this.fs);
    this.lastStatus = Object.freeze({ state: 'BUNDLE_READY', reason: 'MINIMUM_LIVE_EVIDENCE_CAPTURED' });
    return true;
  }
}

function getProcessExactEnvironmentEvidenceRecorder({ appDir = __dirname, env = process.env } = {}) {
  if (processRecorderInitialized) return processRecorder;
  processRecorderInitialized = true;
  const outputPath = String(env.SENTINEL_L3_EVIDENCE_OUTPUT || '').trim();
  const environmentId = String(env.SENTINEL_L3_ENVIRONMENT_ID || '').trim();
  if (!outputPath && !environmentId) return null;
  if (!outputPath || !environmentId) throw new Error('L3_CAPTURE_REQUIRES_OUTPUT_AND_ENVIRONMENT_ID');
  if (String(env.SENTINEL_WOW_SAVEDVARIABLES_PATH || '').trim()) {
    throw new Error('L3_CAPTURE_REJECTS_SAVEDVARIABLES_OVERRIDE');
  }
  processRecorder = new ExactEnvironmentEvidenceRecorder({
    outputPath,
    environmentId,
    packagedProvenance: readPackagedBuildProvenance(appDir),
  });
  return processRecorder;
}

function resetProcessExactEnvironmentEvidenceRecorderForTests() {
  processRecorderInitialized = false;
  processRecorder = null;
}

module.exports = {
  ExactEnvironmentEvidenceRecorder,
  atomicWriteJson,
  deriveCapabilityClaims,
  getProcessExactEnvironmentEvidenceRecorder,
  normalizeAcceptedCheckpoint,
  normalizeHandshake,
  normalizeHealth,
  normalizePackagedProvenance,
  resetProcessExactEnvironmentEvidenceRecorderForTests,
};
