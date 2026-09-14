const fs = require('node:fs');
const path = require('node:path');

const REQUIRED_APP_FILES = Object.freeze([
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

function readPackageMetadata(appDir) {
  const packagePath = path.join(appDir, 'package.json');
  const parsed = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
  return parsed;
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
  if (metadata.main !== 'main.js') {
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
    signed: false,
  };
}

module.exports = {
  REQUIRED_APP_FILES,
  inspectPackagedLayout,
  readPackageMetadata,
};
