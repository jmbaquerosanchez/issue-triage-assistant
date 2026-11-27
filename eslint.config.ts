import js from '@eslint/js';
import { defineConfig, globalIgnores } from 'eslint/config';
import tseslint from 'typescript-eslint';
import { noModuleInternals } from './lint/no-module-internals.ts';

export default defineConfig([
  globalIgnores(['dist/', '.pack/', 'docs/', '.agents/', '.claude/']),
  {
    linterOptions: {
      // A suppression that no longer suppresses anything fails: that is how
      // lint/fixture/ shows the rule against module internals firing.
      reportUnusedDisableDirectives: 'error',
    },
  },
  js.configs.recommended,
  tseslint.configs.recommended,
  {
    plugins: { local: { rules: { 'no-module-internals': noModuleInternals } } },
    rules: { 'local/no-module-internals': 'error' },
  },
  {
    files: ['lint/fixture/**'],
    rules: { 'local/no-module-internals': ['error', { root: 'lint/fixture' }] },
  },
  {
    files: ['src/bin.ts'],
    rules: {
      'no-restricted-syntax': [
        'error',
        ...['ImportDeclaration', 'ExportNamedDeclaration[source]', 'ExportAllDeclaration'].map((selector) => ({
          selector,
          message: "The bin's entry file has no imports: on an older Node they would fail before its version check.",
        })),
      ],
    },
  },
]);
