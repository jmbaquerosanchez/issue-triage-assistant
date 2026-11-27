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

- **Quick**: `pnpm typecheck && pnpm lint && pnpm test`. Seconds, with no build: the tests of `src/` run on the `.ts` sources.
- **Full**: `pnpm typecheck && pnpm lint && pnpm test && pnpm test:e2e`. `test:e2e` builds the package with `tsc`, packs it with `pnpm pack` and runs the tarball as `npx` would.
- **Before pushing**: *Full*. It is what CI runs on Ubuntu, macOS and Windows, so a red CI points at a platform difference, not at something left unrun.

## Test seams

The project's agreed seams. `/jmb-tdd` only writes tests at agreed seams, and an agent working with no human present cannot agree on them on the spot: it takes them from here.

Copied from § Testing Decisions › Test seams of `docs/spec.md`, which binds when the two differ. "Doubles" means the fake models, the fake GitHub, the scenarios and the recorded responses, all in `test/support/`.

| Seam | What is tested there | Where its tests and doubles live | Command for one file |
|---|---|---|---|
| `retrieval` (`buildIndex` and `findDuplicates`) | What a replay sees under a cutoff: renames, later comments, ended pieces, BM25 statistics at the instant and `statsAt`. The three scopes and the cutoffs they reject. Text preparation and tokenizer applied to both sides. The piece of each issue, which gives the excerpt and is the one reranked; the vector leg's 200 issues; RRF, reranking the top 20, `exclude` and `limit`. The facts, the original from `markings` included. An index file opens with no vector cache. Exact scores, which travel in `Candidate` | `src/retrieval/*.test.ts`; fake models, scenarios | `node --test <file>` |
| `markings` | Every signal and wording, the maintainer test, the direction, a marking undone or redone, several originals, and every marking set aside: own author, deleted account, another repository, a pull request | `src/markings/*.test.ts`; one scenario per case | `node --test <file>` |
| `ingestion` | A cut-off and resumed ingestion equals an uninterrupted one and does not move the snapshot date; a disappeared issue found through the `totalCount` mismatch and ended at the last snapshot that matched; a deleted comment ending at its event; an `updatedAt` tie at a page boundary; the quota wait. `reprocess` gives the same history. Responses recorded from this repository's tracker parse | `src/ingestion/*.test.ts`; fake GitHub, recorded responses, injected `sleep` | `node --test <file>` |
| `workspace` | States (first ingestion running or stopped, ready, demo) and the repository list. Number → text from the index or from GitHub, and its exclusion. The snapshot date in the output. Two ingestions, at T1 and then at T2, give the same live index as one at T2, and a disappeared issue leaves it. An ingestion embeds only new texts, counted on the fake embedder. A reader seeing the new generation at its next call, while another still holds the old one. A second ingestion refused, and the lock freed when its process dies. A demo index installed, refused over a real ingestion, and replaced by a real one. The replay line. A live index built for another default, searched with the configuration it records and reported by `status` | `src/workspace/*.test.ts`; fake GitHub, fake models, temporary data directory | `node --test <file>` |
| `demo` (build and fetch) | Only live pieces and the default's legs, the exclusion list applied, no history and no logins, the eval results carried, the NOTICE. A checksum mismatch rejected | `src/demo/*.test.ts`; scenarios, fake models, fake GitHub | `node --test <file>` |
| `eval`: ground truth | Clusters on `markings`, the June 2018 and 90-day bounds, every case exclusion; triage-bench's extraction | `src/eval/*.test.ts`; one scenario per case | `node --test <file>` |
| `eval`: the run | End to end on the synthetic repository with its leak traps: exact ranks and recall per run, each of the ladder's steps with its case set, `statsAt` and new issue text, the default's top 5, the GitHub row from stored responses | `src/eval/*.test.ts`; fake models, fake GitHub | `node --test <file>` |
| `eval`: the report | Results files and verdicts → markdown: metrics, the seeded cluster bootstrap, paired differences, the default rule and its tie-breaks | `src/eval/*.test.ts`; hand-written results files | `node --test <file>` |
| Real `models`: the CI guard | The embedder against reference vectors and the reranker against reference scores, with the thresholds from `offline/` | `src/models/*.test.ts`; references in `test/support/`, written by the offline script | `node --test <file>` |
| `cli` from the sources | What a clone runs with no build, through `src/bin.ts` in a subprocess: the dispatcher (`--help`, bad usage exiting 2) and the bin's Node version check, on a version faked by a preload. The commands themselves are covered end to end | `src/cli/*.test.ts`; `test/support/run-cli.ts`, `test/support/fake-node-version.ts` | `node --test <file>` |
| The packed package, end to end | The `bin` from the tarball run as `npx` runs it: `--help`, and the Node version message on an older Node. The fixture index built by `ingest`, `eval run` and `build-demo-index` against the fake. `demo` against it: download, checksum, installation, the example search with its replay line, the NOTICE line. `find_duplicates` over stdio: by number, by text, an issue not ingested, an unknown repository. Real models | `test/e2e/*.test.ts`; `test/support/run-cli.ts` | `node --test <file>`, after the build and `pnpm pack`, which `pnpm pack:e2e` runs |

**Not seams of their own:**

- `history` and `github`, tested through whoever writes and reads them;
- the BM25 scorer, the vector scan, the tokenizers and cleaning, internal seams of `retrieval` tested through `findDuplicates`;
- `mcp`, and the commands of `cli`, which are thin and covered end to end; the dispatcher and the bin's version check have the `cli` seam above.

`ingestion` is a seam apart from `workspace` because its tests need what `workspace` does not expose: cutting an ingestion off at a chosen request, the fake's instant, and reading the history it wrote.
