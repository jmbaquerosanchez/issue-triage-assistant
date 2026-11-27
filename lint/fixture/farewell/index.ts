import { greet } from '../greeting/index.ts';
// eslint-disable-next-line local/no-module-internals -- the rule must fire here; see lint/fixture/README.md
import { hello } from '../greeting/words.ts';

export function farewell(name: string): string {
  return `${greet(name)}, and goodbye (${hello.length})`;
}
