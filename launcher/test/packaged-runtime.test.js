const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const {
  REQUIRED_APP_FILES,
  inspectPackagedLayout,
  readPackagedBuildProvenance,
} = require('../packaged-runtime');

const SOURCE_SHA = 'a'.repeat(40);

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-packaged-runtime-'));
  const resourcesPath = path.join(root, 'resources');
  const appDir = path.join(resourcesPath, 'app');
  fs.mkdirSync(appDir, { recursive: true });

  for (const relativePath of REQUIRED_APP_FILES) {
    const target = path.join(appDir, relativePath);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, '// fixture\n', 'utf8');
  }
  fs.writeFileSync(
    path.join(appDir, 'package.json'),
    JSON.stringify({
      name: 'sentinel-launcher',
      version: '0.2.0',
      main: 'bootstrap.js',
      dependencies: { electron: '37.2.0' },
      sentinelPackaging: { electronVersion: '37.2.0' },
    }),
    'utf8',
  );
  fs.writeFileSync(
    path.join(appDir, 'build-provenance.json'),
    JSON.stringify({
      schema: 'sentinel.packaged-companion-runtime.v1',
      sourceSha: SOURCE_SHA,
      target: 'win32-x64',
      packageVersion: '0.2.0',
      electronVersion: '37.2.0',
      signed: false,
    }),
    'utf8',
  );

  return { root, resourcesPath, appDir };
}

test('accepts the bounded unpacked Windows Companion payload', () => {
  const { root, resourcesPath } = fixture();
  try {
    const result = inspectPackagedLayout({
      resourcesPath,
      electronVersion: '37.2.0',
      platform: 'win32',
      executablePath: path.join(root, 'SENTINEL Companion.exe'),
    });
    assert.equal(result.status, 'pass');
    assert.equal(result.main, 'bootstrap.js');
    assert.equal(result.electronVersion, '37.2.0');
    assert.equal(result.applicationPayload, 'resources/app');
    assert.equal(result.signed, false);
    assert.equal(result.sourceSha, SOURCE_SHA);
    assert.equal(result.sourceBound, true);
    assert.match(result.provenanceFileSha256, /^[0-9a-f]{64}$/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('reads bounded embedded build provenance', () => {
  const { root, appDir } = fixture();
  try {
    const result = readPackagedBuildProvenance(appDir);
    assert.equal(result.schema, 'sentinel.packaged-companion-runtime.v1');
    assert.equal(result.sourceSha, SOURCE_SHA);
    assert.equal(result.sourceBound, true);
    assert.equal(result.target, 'win32-x64');
    assert.match(result.provenanceFileSha256, /^[0-9a-f]{64}$/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('fails closed when a runtime source is missing', () => {
  const { root, resourcesPath, appDir } = fixture();
  try {
    fs.rmSync(path.join(appDir, 'companion-worker.js'));
    assert.throws(
      () => inspectPackagedLayout({
        resourcesPath,
        electronVersion: '37.2.0',
        platform: 'win32',
        executablePath: path.join(root, 'SENTINEL Companion.exe'),
      }),
      /missing required files: companion-worker\.js/,
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('rejects Electron drift and bundled dependency/test trees', () => {
  const first = fixture();
  try {
    assert.throws(
      () => inspectPackagedLayout({
        resourcesPath: first.resourcesPath,
        electronVersion: '38.0.0',
        platform: 'win32',
        executablePath: path.join(first.root, 'SENTINEL Companion.exe'),
      }),
      /Electron version mismatch/,
    );
  } finally {
    fs.rmSync(first.root, { recursive: true, force: true });
  }

  const second = fixture();
  try {
    fs.mkdirSync(path.join(second.appDir, 'node_modules'));
    assert.throws(
      () => inspectPackagedLayout({
        resourcesPath: second.resourcesPath,
        electronVersion: '37.2.0',
        platform: 'win32',
        executablePath: path.join(second.root, 'SENTINEL Companion.exe'),
      }),
      /node_modules must not be bundled/,
    );
  } finally {
    fs.rmSync(second.root, { recursive: true, force: true });
  }
});

test('rejects non-Windows evidence and executable renaming drift', () => {
  const first = fixture();
  try {
    assert.throws(
      () => inspectPackagedLayout({
        resourcesPath: first.resourcesPath,
        electronVersion: '37.2.0',
        platform: 'linux',
        executablePath: path.join(first.root, 'SENTINEL Companion.exe'),
      }),
      /requires win32/,
    );
  } finally {
    fs.rmSync(first.root, { recursive: true, force: true });
  }

  const second = fixture();
  try {
    assert.throws(
      () => inspectPackagedLayout({
        resourcesPath: second.resourcesPath,
        electronVersion: '37.2.0',
        platform: 'win32',
        executablePath: path.join(second.root, 'electron.exe'),
      }),
      /unexpected packaged executable name/,
    );
  } finally {
    fs.rmSync(second.root, { recursive: true, force: true });
  }
});

test('rejects packaged provenance drift', () => {
  const { root, resourcesPath, appDir } = fixture();
  try {
    fs.writeFileSync(
      path.join(appDir, 'build-provenance.json'),
      JSON.stringify({
        schema: 'sentinel.packaged-companion-runtime.v1',
        sourceSha: SOURCE_SHA,
        target: 'win32-x64',
        packageVersion: '0.1.0',
        electronVersion: '37.2.0',
        signed: false,
      }),
      'utf8',
    );
    assert.throws(
      () => inspectPackagedLayout({
        resourcesPath,
        electronVersion: '37.2.0',
        platform: 'win32',
        executablePath: path.join(root, 'SENTINEL Companion.exe'),
      }),
      /provenance package version mismatch/,
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
