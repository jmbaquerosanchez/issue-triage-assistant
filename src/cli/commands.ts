/**
 * A subcommand. It parses its own arguments, with `parseArgs` from `node:util`
 * and `strict: true`, and returns its exit code: 0 done, 1 failed. Bad usage
 * throws a `UsageError` or lets `parseArgs`'s error through, and exits 2.
 */
export interface Command {
  name: string;
  /** What follows the name in its usage line, such as `<owner/repo> [--full]`. */
  usage: string;
  /** One line for `--help`. */
  summary: string;
  /** Listed in the "Maintenance" group at the end of `--help`. */
  maintenance?: boolean;
  run(args: string[]): Promise<number>;
}

/** Bad usage: the CLI prints its message on stderr and exits 2. */
export class UsageError extends Error {
  override name = 'UsageError';
}

/** Every subcommand, in the order `--help` lists them. */
export const commands: readonly Command[] = [];
