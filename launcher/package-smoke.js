const fs = require('node:fs');
const path = require('node:path');
const { app } = require('electron');
const { inspectPackagedLayout } = require('./packaged-runtime');

function writeEvidence(payload) {
  const outputPath = process.env.SENTINEL_PACKAGE_SMOKE_OUTPUT;
  if (!outputPath) {
    throw new Error('SENTINEL_PACKAGE_SMOKE_OUTPUT is required');
  }
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

app.whenReady().then(() => {
  try {
    const layout = inspectPackagedLayout({
      resourcesPath: process.resourcesPath,
      electronVersion: process.versions.electron,
      platform: process.platform,
      executablePath: process.execPath,
    });

    // Loading these modules from resources/app proves that the packaged payload
    // keeps the runtime module graph resolvable without node_modules or ASAR.
    require('./companion-process');
    require('./core-session');
    require('./exact-environment-evidence');
    require('./runtime-health');
    require('./voice-runtime');
    require('./wow-savedvariables');

    writeEvidence({
      schema: 'sentinel.packaged-companion-smoke.v1',
      status: 'pass',
      sourceSha: process.env.SENTINEL_SOURCE_SHA || null,
      ...layout,
      runtimeModulesLoaded: [
        'companion-process',
        'core-session',
        'exact-environment-evidence',
        'runtime-health',
        'voice-runtime',
        'wow-savedvariables',
      ],
    });
    app.exit(0);
  } catch (error) {
    try {
      writeEvidence({
        schema: 'sentinel.packaged-companion-smoke.v1',
        status: 'fail',
        sourceSha: process.env.SENTINEL_SOURCE_SHA || null,
        error: error instanceof Error ? error.message : String(error),
      });
    } finally {
      console.error(error);
      app.exit(1);
    }
  }
});
