// Prove the scoped dependency replacement preserves Next's real rootDir behavior.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createRequire } = require('node:module');
const { spawnSync } = require('node:child_process');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-lint-glob-'));
try {
  fs.mkdirSync(path.join(root, 'web')); fs.mkdirSync(path.join(root, 'site'));
  fs.writeFileSync(path.join(root, 'file.ts'), 'fixture');
  for (const surface of process.argv.length > 2 ? process.argv.slice(2) : ['web', 'site']) {
    assert.ok(['web','site'].includes(surface));
    const requireSurface = createRequire(path.resolve(__dirname, '..', surface, 'package.json'));
    const requireEslint = createRequire(requireSurface.resolve('eslint'));
    const legacyMatch = requireEslint('minimatch');
    assert.equal(requireEslint('minimatch/package.json').name, '@sentinel/minimatch-legacy-compat');
    assert.equal(typeof legacyMatch, 'function');
    for (const [file, pattern, options, expected] of [
      ['app/page.tsx', '**/*.{ts,tsx}', {}, true],
      ['app/page.js', '**/*.{ts,tsx}', {}, false],
      ['.next/cache/file.js', '**/*.js', {}, false],
      ['.next/cache/file.js', '**/*.js', {dot:true}, true],
      ['app/page.tsx', '!**/*.js', {}, true],
      ['app/page.tsx', '**/*.TSX', {nocase:true}, true],
    ]) assert.equal(legacyMatch(file, pattern, options), expected);
    assert.deepEqual(legacyMatch.match(['a.ts', 'b.js'], '*.ts'), ['a.ts']);
    assert.equal(legacyMatch.defaults({nocase:true})('PAGE.TSX', '*.tsx'), true);
    assert.equal(new legacyMatch.Minimatch('**/*.tsx').match('app/page.tsx'), true);
    assert.ok(legacyMatch.makeRe('**/*.tsx').test('app/page.tsx'));
    assert.deepEqual(legacyMatch.braceExpand('page.{ts,tsx}'), ['page.ts','page.tsx']);
    const requireEstree = createRequire(requireSurface.resolve('@typescript-eslint/typescript-estree'));
    assert.equal(requireEstree('minimatch/package.json').version, '11.0.1');
    assert.equal(requireEstree('minimatch').minimatch('app/page.tsx', '**/*.tsx'), true);
    const lint = spawnSync(process.execPath, [
      path.join(path.dirname(requireSurface.resolve('eslint/package.json')), 'bin/eslint.js'),
      '--stdin', '--stdin-filename', 'app/__lint_guard__.tsx', '--format', 'json',
      '--rule', 'import/no-internal-modules:["error",{"forbid":["**/internal/**"]}]',
    ], {cwd:path.resolve(__dirname,'..',surface), encoding:'utf8', timeout:30000,
      input:"import hidden from './internal/private'; export default function Page(){return <img src={hidden}/>;}"});
    assert.equal(lint.status, 1, lint.stdout + lint.stderr);
    const ruleIds = JSON.parse(lint.stdout).flatMap(file => file.messages.map(message => message.ruleId));
    assert.ok(ruleIds.includes('jsx-a11y/alt-text'), lint.stdout);
    assert.ok(ruleIds.includes('import/no-internal-modules'), lint.stdout);
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
