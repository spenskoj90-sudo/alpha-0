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
    const { KnowledgePresentation } = require('./knowledge-presentation');
    require('./knowledge-runtime');
    const knowledge = new KnowledgePresentation({
      directory: path.join(app.getPath('userData'), 'knowledge-smoke'),
      session: { knowledgeContext: { origin: 'https://fixture.invalid', sessionId: 'smoke' }, cancelKnowledge() {} },
      getTrustedContext: () => null, getTrustedObservation: () => null,
    });
    // Real packaged module graph exercises the safe uncalibrated lifecycle.
    void knowledge.start();
    if (knowledge.status().state !== 'WAITING_FOR_VERIFIED_PROFILE' || knowledge.presentations().length !== 0) {
      throw new Error('unverified knowledge lifecycle must fail closed');
    }
    knowledge.stop();
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
        'knowledge-runtime',
        'knowledge-presentation',
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
