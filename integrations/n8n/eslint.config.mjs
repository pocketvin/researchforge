import { createRequire } from 'node:module';

// Reuse the pinned frontend lint toolchain; the integration adds no npm dependencies.
const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
const js = require('@eslint/js');

export default [{
  files: ['**/*.mjs', '**/*.js'],
  languageOptions: {
    globals: { URL: 'readonly', process: 'readonly', console: 'readonly', $input: 'readonly', $execution: 'readonly',
      $runIndex: 'readonly', $: 'readonly' },
    parserOptions: { ecmaFeatures: { globalReturn: true } },
  },
  rules: { ...js.configs.recommended.rules },
}, {
  files: ['**/code/*.js'],
  languageOptions: { sourceType: 'commonjs' },
}];
