# The rule against module internals, firing

Two toy modules, linted with `lint/fixture/` as their root. `farewell/index.ts` imports `greeting`'s entry file, which the rule allows, and one of its internals, which the rule forbids. That import carries a suppression, and lint fails on a suppression that suppresses nothing: if the rule stopped firing, `pnpm lint` would fail.
