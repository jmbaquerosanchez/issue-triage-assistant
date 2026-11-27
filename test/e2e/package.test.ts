import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, before, test } from 'node:test';
import { runPackedCli } from '../support/run-cli.ts';

let dir: string;
before(() => {
  dir = mkdtempSync(join(tmpdir(), 'issue-triage-assistant-e2e-'));
});
after(() => {
  rmSync(dir, { recursive: true, force: true, maxRetries: 3 });
});

test('the packed package, run as npx runs it, prints the usage for --help and exits 0', () => {
  const run = runPackedCli(dir, ['--help']);

  assert.equal(run.status, 0, run.stderr);
  assert.match(run.stdout, /^Usage: issue-triage-assistant <command> \[options\]\n/);
});

test('the packed package on an older Node prints which Node it needs and exits 1', () => {
  const run = runPackedCli(dir, ['--help'], { nodeVersion: '24.14.0' });

  assert.equal(run.stdout, '');
  assert.equal(run.status, 1);
  assert.match(run.stderr, /issue-triage-assistant needs Node ≥ 24\.15; this is Node 24\.14\.0\n/);
});
