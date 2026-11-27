import path from 'node:path';
import type { Rule } from 'eslint';

/**
 * Forbids importing a module's internals. A module is a folder directly under
 * `root` (`src` by default), and its single entry file is its `index.ts`: a
 * relative import from outside the module that lands inside it must name that
 * file. A module's own files import each other freely.
 */
export const noModuleInternals: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: { description: "Forbid importing a module's internals: anything but its entry file" },
    schema: [{ type: 'object', properties: { root: { type: 'string' } }, additionalProperties: false }],
    messages: {
      internal: "'{{source}}' reaches inside the module {{module}}: import its entry file, {{entry}}",
    },
  },
  create(context) {
    const options: { root?: string } = context.options[0] ?? {};
    const root = path.resolve(context.cwd, options.root ?? 'src');
    const moduleOf = (file: string): string | undefined => {
      const relative = path.relative(root, file);
      if (relative.startsWith('..') || path.isAbsolute(relative)) return undefined;
      const [first, ...rest] = relative.split(path.sep);
      return rest.length > 0 ? first : undefined;
    };
    const importer = moduleOf(context.filename);

    function check(node: Rule.Node): void {
      if (!('source' in node) || node.source?.type !== 'Literal') return;
      const source = node.source.value;
      if (typeof source !== 'string' || !source.startsWith('.')) return;
      const target = path.resolve(path.dirname(context.filename), source);
      const module = moduleOf(target);
      if (module === undefined || module === importer) return;
      const entry = path.join(root, module, 'index.ts');
      if (target === entry) return;
      context.report({
        node,
        messageId: 'internal',
        data: { source, module, entry: path.relative(context.cwd, entry).split(path.sep).join('/') },
      });
    }

    return {
      ImportDeclaration: check,
      ExportNamedDeclaration: check,
      ExportAllDeclaration: check,
      ImportExpression: check,
    };
  },
};
