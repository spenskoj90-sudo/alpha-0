'use strict';
// Lint-only facade: preserve the callable CJS API without restoring the vulnerable
// regex compiler removed in minimatch 11. All matches use upstream's patched engine.
const modern = require('minimatch-modern');
const compat = Object.assign((...args) => modern.minimatch(...args), modern);
// eslint-plugin-import/no-internal-modules only consumes makeRe(...).test(path).
// This intentionally returns a test-only matcher, not a generated RegExp.
compat.makeRe = (pattern, options) => Object.freeze({
  test: value => modern.minimatch(value, pattern, options),
});
module.exports = compat;
