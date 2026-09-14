const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const REQUIRED_APP_FILES = Object.freeze([
  'bootstrap.js',
  'build-provenance.json',
  'companion-process.js',
  'companion-worker.js',
  'core-session.js',
  'index.html',
  'main.js',
  'overlay-preload.js',
  'overlay-renderer.js',
  'overlay-state.js',
  'overlay.html',
  'package-smoke.js',
  'package.json',
  'packaged-runtime.js',
  'preload.js',
  'renderer.js',
  'runtime-health.js',
  'voice-runtime.js',
  'wow-savedvariables.js',
]);

const SOURCE_SHA_RE = /^[0-9a-f]{40}$/;
const MAX_PROVENANCE_BYTES = 16 * 1024;

function readPackageMetadata(appDir) {
  const packagePath = path.join(appDir, 'package.json');
  return JSON.parse(fs.readFileSync(packagePath, 'utf8'));
}

function readPackagedBuildProvenance(appDir) {
  const provenancePath = path.join(appDir, 'build-provenance.json');
  const stat = fs.statSync(provenancePath, { throwIfNoEntry: false });
  if (!stat?.isFile()) throw new Error('packaged build provenance is missing');
  if (stat.size < 2 || stat.size > MAX_PROVENANCE_BYTES) throw new Error('packaged build provenance size is invalid');
  const raw = fs.readFileSync(provenancePath);
  let value;
  try { value = JSON.parse(raw.toString('utf8')); } catch { throw new Error('packaged build provenance is invalid JSON'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('packaged build provenance must be an object');
  const allowed = new Set(['schema', 'sourceSha', 'target', 'packageVersion', 'electronVersion', 'signed']);
  if (Object.keys(value).some(key => !allowed.has(key))) throw new Error('packaged build provenance contains unexpected fields');
  if (value.schema !== 'sentinel.packaged-companion-runtime.v1') throw new Error('packaged build provenance schema mismatch');
  const sourceSha = String(value.sourceSha || '');
  if (sourceSha !== 'local-unbound' && !SOURCE_SHA_RE.test(sourceSha)) throw new Error('packaged build provenance source SHA is invalid');
  if (value.target !== 'win32-x64') throw new Error('packaged build provenance target mismatch');
  if (typeof value.packageVersion !== 'string' || !value.packageVersion || value.packageVersion.length > 64) throw new Error('packaged build provenance package version is invalid');
  if (typeof value.electronVersion !== 'string' || !value.electronVersion || value.electronVersion.length > 32) throw new Error('packaged build provenance Electron version is invalid');
  if (typeof value.signed !== 'boolean') throw new Error('packaged build provenance signed flag is invalid');
  return Object.freeze({
    schema: value.schema,
    sourceSha,
    sourceBound: SOURCE_SHA_RE.test(sourceSha),
    target: value.target,
    packageVersion: value.packageVersion,
    electronVersion: value.electronVersion,
    signed: value.signed,
    provenanceFileSha256: crypto.createHash('sha256').update(raw).digest('hex'),
  });
}

function inspectPackagedLayout({
  resourcesPath,
  electronVersion,
  platform,
  executablePath,
}) {
  if (!resourcesPath || typeof resourcesPath !== 'string') {
    throw new Error('resourcesPath is required');
  }
  if (platform !== 'win32') {
    throw new Error(`packaged host evidence requires win32, got ${platform}`);
  }

  const appDir = path.join(resourcesPath, 'app');
  if (!fs.statSync(appDir, { throwIfNoEntry: false })?.isDirectory()) {
    throw new Error('resources/app directory is missing');
  }

  const metadata = readPackageMetadata(appDir);
  const packaging = metadata.sentinelPackaging || {};
  const expectedElectronVersion = String(packaging.electronVersion || '');
  const declaredElectronVersion = String(metadata.dependencies?.electron || '');

  if (!expectedElectronVersion) {
    throw new Error('sentinelPackaging.electronVersion is missing');
  }
  if (declaredElectronVersion !== expectedElectronVersion) {
    throw new Error('Electron dependency must be pinned exactly to sentinelPackaging.electronVersion');
  }
  if (String(electronVersion) !== expectedElectronVersion) {
    throw new Error(
      `packaged Electron version mismatch: expected ${expectedElectronVersion}, got ${electronVersion}`,
    );
  }
  if (metadata.main !== 'bootstrap.js') {
    throw new Error(`unexpected packaged main entrypoint: ${metadata.main}`);
  }

  const missingFiles = REQUIRED_APP_FILES.filter(
    (relativePath) => !fs.statSync(path.join(appDir, relativePath), { throwIfNoEntry: false })?.isFile(),
  );
  if (missingFiles.length > 0) {
    throw new Error(`packaged app is missing required files: ${missingFiles.join(', ')}`);
  }

  if (fs.existsSync(path.join(appDir, 'node_modules'))) {
    throw new Error('node_modules must not be bundled into the Companion application payload');
  }
  if (fs.existsSync(path.join(appDir, 'test'))) {
    throw new Error('launcher test sources must not be bundled into the Companion application payload');
  }

  const executableName = path.basename(executablePath || '');
  if (executableName.toLowerCase() !== 'sentinel companion.exe') {
    throw new Error(`unexpected packaged executable name: ${executableName}`);
  }

  const provenance = readPackagedBuildProvenance(appDir);
  if (provenance.packageVersion !== String(metadata.version || '')) {
    throw new Error('packaged build provenance package version mismatch');
  }
  if (provenance.electronVersion !== expectedElectronVersion) {
    throw new Error('packaged build provenance Electron version mismatch');
  }

  return {
    status: 'pass',
    platform,
    executableName,
    electronVersion: expectedElectronVersion,
    packageVersion: String(metadata.version || ''),
    main: metadata.main,
    requiredFileCount: REQUIRED_APP_FILES.length,
    nodeModulesBundled: false,
    testSourcesBundled: false,
    applicationPayload: 'resources/app',
    signed: provenance.signed,
    sourceSha: provenance.sourceSha,
    sourceBound: provenance.sourceBound,
    provenanceFileSha256: provenance.provenanceFileSha256,
  };
}

module.exports = {
  REQUIRED_APP_FILES,
  inspectPackagedLayout,
  readPackageMetadata,
  readPackagedBuildProvenance,
};
