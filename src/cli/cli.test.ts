import assert from 'node:assert/strict';
import { test } from 'node:test';
import { runSourceCli } from '../../test/support/run-cli.ts';

for (const flag of ['--help', '-h']) {
  test(`${flag} prints the usage on stdout and exits 0`, () => {
    const run = runSourceCli([flag]);

    assert.equal(run.stderr, '');
    assert.equal(run.status, 0);
    assert.match(run.stdout, /^Usage: issue-triage-assistant <command> \[options\]\n/);
  });
}

test('--help says that the human text may change and scripts should use --json', () => {
  const run = runSourceCli(['--help']);

  assert.match(run.stdout, /\nThe human text may change in any version; scripts should use --json\.\n$/);
});

test('no command is bad usage: the usage goes to stderr and it exits 2', () => {
  const run = runSourceCli([]);

  assert.equal(run.stdout, '');
  assert.equal(run.status, 2);
  assert.match(run.stderr, /^Usage: issue-triage-assistant <command> \[options\]\n/);
});

test('an unknown command is bad usage and exits 2', () => {
  const run = runSourceCli(['frobnicate', '--json']);

  assert.equal(run.stdout, '');
  assert.equal(run.status, 2);
  assert.equal(
    run.stderr,
    "issue-triage-assistant: unknown command 'frobnicate'\nRun 'issue-triage-assistant --help' for usage.\n",
  );
});

test('an unknown option before the command is bad usage and exits 2', () => {
  const run = runSourceCli(['--frobnicate']);

  assert.equal(run.stdout, '');
  assert.equal(run.status, 2);
  assert.match(run.stderr, /^issue-triage-assistant: Unknown option '--frobnicate'/);
  assert.match(run.stderr, /\nRun 'issue-triage-assistant --help' for usage\.\n$/);
});

for (const version of ['22.22.0', '24.9.0', '24.14.1']) {
  test(`on Node ${version} the bin prints which Node it needs and exits 1`, () => {
    const run = runSourceCli(['--help'], { nodeVersion: version });

    assert.equal(run.stdout, '');
    assert.equal(run.status, 1);
    assert.equal(run.stderr, `issue-triage-assistant needs Node ≥ 24.15; this is Node ${version}\n`);
  });
}

for (const version of ['24.15.0', '25.0.0']) {
  test(`on Node ${version} the bin runs`, () => {
    const run = runSourceCli(['--help'], { nodeVersion: version });

    assert.equal(run.stderr, '');
    assert.equal(run.status, 0);
  });
}
