import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

export interface CliRun {
  status: number | null;
  stdout: string;
  stderr: string;
}

export interface CliOptions {
  /** The Node version the bin sees instead of the real one, to test its version check. */
  nodeVersion?: string;
}

const sourceBin = fileURLToPath(new URL('../../src/bin.ts', import.meta.url));
const packedTarball = fileURLToPath(new URL('../../.pack/issue-triage-assistant.tgz', import.meta.url));
const fakeNodeVersion = new URL('./fake-node-version.ts', import.meta.url).href;

/** Runs the bin from the .ts sources, as a clone runs it with no build. */
export function runSourceCli(args: readonly string[], options: CliOptions = {}): CliRun {
  const preload = options.nodeVersion === undefined ? [] : ['--import', fakeNodeVersion];
  const result = spawnSync(process.execPath, [...preload, sourceBin, ...args], {
    encoding: 'utf8',
    env: { ...process.env, ...fakeNodeVersionEnv(options) },
  });
  if (result.error) throw result.error;
  return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

/**
 * Runs the packed package's bin as `npx` runs it: npm installs the tarball that
 * `pnpm pack:e2e` built and runs the bin through the shim it links. `dir` is a
 * temporary directory of the test's own, which holds npm's cache and is the
 * working directory, so no install from elsewhere is reused.
 */
export function runPackedCli(dir: string, args: readonly string[], options: CliOptions = {}): CliRun {
  if (!existsSync(packedTarball)) {
    throw new Error(`${packedTarball} is missing: build and pack the package with pnpm pack:e2e first`);
  }
  const npxArgs = ['--yes', `--package=${packedTarball}`, '--', 'issue-triage-assistant', ...args];
  // Through a shell, as a user types it: on Windows npx is a .cmd script, which
  // Node only spawns through one. A single command line, since Node deprecates
  // passing an argument list along with `shell`.
  const result = spawnSync(['npx', ...npxArgs.map(quoteForShell)].join(' '), {
    shell: true,
    cwd: dir,
    encoding: 'utf8',
    timeout: 120_000,
    env: {
      // pnpm's variables would reach npm as its own configuration.
      ...Object.fromEntries(Object.entries(process.env).filter(([name]) => !/^npm_/i.test(name))),
      npm_config_cache: join(dir, 'npm-cache'),
      npm_config_update_notifier: 'false',
      npm_config_fund: 'false',
      npm_config_audit: 'false',
      ...(options.nodeVersion === undefined ? {} : { NODE_OPTIONS: `--import=${fakeNodeVersion}` }),
      ...fakeNodeVersionEnv(options),
    },
  });
  if (result.error) throw result.error;
  return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

/** The variable that `fake-node-version.ts`, preloaded with `--import`, reads. */
function fakeNodeVersionEnv(options: CliOptions): Record<string, string> {
  return options.nodeVersion === undefined ? {} : { FAKE_NODE_VERSION: options.nodeVersion };
}

function quoteForShell(arg: string): string {
  if (process.platform !== 'win32') return `'${arg.replaceAll("'", "'\\''")}'`;
  // cmd.exe has no escape that holds inside double quotes for these.
  if (/["%!^]/.test(arg)) throw new Error(`cannot pass ${arg} to cmd.exe`);
  return `"${arg}"`;
}
