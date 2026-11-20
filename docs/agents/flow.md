# Flow

Translates into this project the roles the flow skills speak in: `jmb-implement-ticket`, `jmb-review-pr`, `jmb-sync` and `jmb-implement-frontier`. They cite each section by its heading and each field by its bold label.

Whatever goes between `<…>` in a command is replaced by the skill when it runs it: `<n>` is the ticket number, and the others are defined by their field. Each command runs at the root of the checkout where the work happens, the main checkout or the ticket's worktree, unless its field says otherwise.

## Tickets

Which tickets the flow carries: the open ones with the label.

- **Label**: `ready-for-agent`

## Spec

The tickets cite its sections in their `Spec:` line.

- **Path**: `docs/spec.md`
- **Analogies**: § Decisions by analogy

## Verification

What runs at each moment, with its why when it is not obvious.

There is no code yet: the ticket that scaffolds the project fills in this section and § Test seams.

- **Quick**: pending.
- **Full**: pending.
- **Before pushing**: pending.

## Test seams

The project's agreed seams. `/jmb-tdd` only writes tests at agreed seams, and an agent working with no human present cannot agree on them on the spot: it takes them from here.

| Seam | What is tested there | Where its tests and doubles live | Command for one file |
|---|---|---|---|
| Pending | Agreed by the ticket that scaffolds the project | — | — |
