import { parseArgs } from 'node:util';
import { commands, UsageError } from './commands.ts';

const bin = 'issue-triage-assistant';

/**
 * Runs the CLI over its arguments, without the node and script paths, and
 * returns the exit code: 0 done, 1 failed, 2 bad usage.
 */
export async function main(argv: readonly string[]): Promise<number> {
  // The options before the first positional are the CLI's own; the command
  // parses everything after its name.
  const at = argv.findIndex((arg) => !arg.startsWith('-'));
  try {
    const { values } = parseArgs({
      args: at === -1 ? [...argv] : argv.slice(0, at),
      options: { help: { type: 'boolean', short: 'h' } },
      strict: true,
    });
    if (values.help) {
      process.stdout.write(help());
      return 0;
    }
    if (at === -1) {
      process.stderr.write(help());
      return 2;
    }
    const name = argv[at];
    const command = commands.find((candidate) => candidate.name === name);
    if (command === undefined) throw new UsageError(`unknown command '${name}'`);
    return await command.run(argv.slice(at + 1));
  } catch (error) {
    if (!isUsageError(error)) throw error;
    process.stderr.write(`${bin}: ${error.message}\nRun '${bin} --help' for usage.\n`);
    return 2;
  }
}

function isUsageError(error: unknown): error is Error {
  if (error instanceof UsageError) return true;
  const code = error instanceof Error && 'code' in error ? error.code : undefined;
  return typeof code === 'string' && code.startsWith('ERR_PARSE_ARGS_');
}

function help(): string {
  const groups = [
    { title: 'Commands', members: commands.filter((command) => !command.maintenance) },
    { title: 'Maintenance', members: commands.filter((command) => command.maintenance) },
  ].filter((group) => group.members.length > 0);
  return [
    `Usage: ${bin} <command> [options]`,
    '',
    'Finds the duplicates of a new GitHub issue in its repository history.',
    ...groups.flatMap(({ title, members }) => [
      '',
      `${title}:`,
      ...members.flatMap((command) => [`  ${bin} ${command.name} ${command.usage}`, `      ${command.summary}`]),
    ]),
    '',
    'Options:',
    '  -h, --help  Show this help',
    '',
    'The human text may change in any version; scripts should use --json.',
    '',
  ].join('\n');
}
