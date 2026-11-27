#!/usr/bin/env node
// The bin's entry file has no imports, and its syntax runs on any Node with ES
// modules. A static import would be loaded before the check below, and on an
// older Node it would fail with an import error instead of this message; npm
// only warns on `engines`.
const [major = 0, minor = 0] = process.versions.node.split('.').map(Number);
if (major < 24 || (major === 24 && minor < 15)) {
  process.stderr.write(`issue-triage-assistant needs Node ≥ 24.15; this is Node ${process.versions.node}\n`);
  process.exitCode = 1;
} else {
  import('./cli/index.ts').then(async ({ main }) => {
    process.exitCode = await main(process.argv.slice(2));
  });
}
