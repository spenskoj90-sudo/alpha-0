// Prove the scoped dependency replacement preserves Next's real rootDir behavior.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createRequire } = require('node:module');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-lint-glob-'));
try {
  fs.mkdirSync(path.join(root, 'web')); fs.mkdirSync(path.join(root, 'site'));
  fs.writeFileSync(path.join(root, 'file.ts'), 'fixture');
  for (const surface of process.argv.length > 2 ? process.argv.slice(2) : ['web', 'site']) {
    assert.ok(['web','site'].includes(surface));
    const requireSurface = createRequire(path.resolve(__dirname, '..', surface, 'package.json'));
    const pluginEntry = requireSurface.resolve('@next/eslint-plugin-next');
    const requirePlugin = createRequire(pluginEntry);
    assert.equal(requirePlugin('fast-glob/package.json').name, 'tinyglobby');
    assert.equal(requirePlugin('fast-glob/package.json').version, '0.2.17');
    const { getRootDirs } = requirePlugin('./utils/get-root-dirs.js');
    // Next consumes these as filesystem paths, not serialized absolute strings.
    // tinyglobby returns relative paths with a directory suffix; prove identity.
    const canonical = dirs => dirs.map(dir => path.resolve(dir)).sort();
    assert.deepEqual(getRootDirs({ cwd: root, settings: {} }), [root]);
    assert.deepEqual(canonical(getRootDirs({ cwd: root, settings: { next: { rootDir: `${root}/*` } } })), [path.join(root,'site'), path.join(root,'web')]);
    assert.deepEqual(canonical(getRootDirs({ cwd: root, settings: { next: { rootDir: [`${root}/web`, `${root}/site`] } } })), [path.join(root,'site'),path.join(root,'web')]);
  }
  console.log('Scoped Next lint glob compatibility PASS');
} finally { fs.rmSync(root, { recursive: true, force: true }); }
