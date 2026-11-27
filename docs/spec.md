# Phase 1: duplicate search and its eval

Phase 1 of issue-triage-assistant: ingesting a target repository's history, finding the duplicates of a new issue, and measuring that search by replaying the repository's own history. Synthesized from [Map: phase-1 spec for duplicate search and its eval](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/2) and the resolutions of its tickets; § Further Notes says which ticket each section comes from. Terms follow `CONTEXT.md`, and the ADRs in `docs/adr/` bind every section.

## Problem Statement

The maintainers of a large open source repository receive a steady stream of new issues, and many of them report something already reported. In godotengine/godot, maintainers have marked about 5,000 issues as duplicates since June 2018, out of 64,500 issues in its history. Recognizing a duplicate means remembering or finding an issue that may have been opened years earlier, described in other words, and retitled since. GitHub's search matches today's text, and the author of a new issue rarely searches before filing it.

Tools that propose duplicates exist, GitHub's own filing-time suggestions among them, but almost none says how often it is right. The one open benchmark that measures duplicate search on GitHub issues over time, triage-bench, measures under conditions that let the future leak into each case: issues are searched by their current text rather than the text they had when the duplicate was filed, candidates come from a window rather than the whole history, bot markings count as ground truth, and keyword statistics count issues opened later. A maintainer has no trustworthy number to decide how far to rely on a proposal, and no way to measure one on their own repository.

Whoever wants to judge the project meets one more obstacle: running it on real data takes a GitHub token, hours of download and hours of embedding.

## Solution

A local tool, the npm package `issue-triage-assistant`, that finds the duplicates of a new issue and measures how well it does so by replaying the target repository's own history.

- **Ingestion.** With a GitHub token, one command downloads a target repository's history (issues, comments, every revision of their text, and timeline events, each with its date) and keeps it up to date. The first ingestion of godot takes hours and resumes if cut off; a daily one takes seconds.
- **Duplicate search.** For a new issue given by number, by URL, or as a draft (title and body), it proposes up to 20 duplicate candidates from hybrid search over the pieces of the history: a keyword score of its own and local embeddings, fused, with an optional local reranker. It needs no API key. Each candidate carries what a maintainer needs to judge it: title, link, state, the original it was marked a duplicate of, and the excerpt that matched. It shows no score.
- **Two surfaces.** A CLI, and a read-only MCP tool, `find_duplicates`, that Claude Code uses over every ingested repository. Nothing writes to GitHub.
- **The eval.** Every eval case, a godot duplicate opened since June 2018, is replayed at its cutoff, seeing only what existed then, text as it stood included. Recall@5 is reported with margins for 15 configurations and baselines, and a ladder of corrections, anchored on triage-bench's own code, shows how much each leak moves the numbers. A stated rule picks the default configuration from those results. The results and the report are committed to this repository and hold no issue text.
- **The demo.** `npx issue-triage-assistant demo` downloads, with no credential of any kind, a ready-built index of godot and searches it from the CLI and from Claude Code, showing, for an eval case, the rank it got in the replay.

## User Stories

### Maintainers using it on their repository

1. As a maintainer, I want to ingest my repository's history with one command and my GitHub token, so that I can search it for duplicates locally.
2. As a maintainer, I want a cut-off first ingestion to resume when I run the same command again, so that a rate limit, a crash or a dropped network does not throw away hours of download.
3. As a maintainer, I want later ingestions to fetch only what changed since the previous one, so that keeping the repository current costs seconds a day.
4. As a maintainer, I want the README to give a cron example for a daily ingestion, so that the history stays current without me.
5. As a maintainer, I want an ingestion that runs out of GitHub quota to wait for the reset and say until when, so that a long first ingestion finishes unattended.
6. As a maintainer, I want a second ingestion of the same repository to be refused with a clear message, so that two runs never write the history at once.
7. As a maintainer, I want an ingestion to end with a summary of what changed (issues, comments, deletions, disappeared issues, pieces embedded, GitHub points, time), so that I can tell it worked.
8. As a maintainer, I want text deleted or edited away at the source to leave present search after the next ingestion, so that a token or a path someone removed from an issue stops showing.
9. As a maintainer, I want to find the duplicate candidates of an issue by its number, so that I can decide whether to close it as a duplicate.
10. As a maintainer, I want to pass an issue URL instead of a number, so that I can paste what is in my browser.
11. As a maintainer, I want each candidate to show its title, link, opening date, and state with its close reason, so that I can judge it at a glance.
12. As a maintainer, I want a candidate that is itself a marked duplicate to name its original, so that I reach the original in one step.
13. As a maintainer, I want each candidate to show the excerpt that matched, the start of its body or the comment with its link, so that I can judge it without opening it.
14. As a maintainer, I want no score in the output, so that I do not read an uncalibrated number as confidence.
15. As a maintainer, I want every output to say up to which date the repository's snapshot reaches, and that issues opened later are not candidates, so that I know what the search could see.
16. As a maintainer, I want an issue opened after the last ingestion to be fetched from GitHub by its number, so that I can triage an issue opened minutes ago.
17. As a maintainer, I want the new issue never to appear among its own candidates.
18. As a maintainer, I want 5 candidates by default and up to 20 on request, so that the list stays short unless I want more.
19. As a maintainer, I want to search my repositories from Claude Code through an MCP tool, so that an agent can propose duplicates during my triage session.
20. As a maintainer, I want one MCP server to serve every repository I ingested, so that I register it once.
21. As a maintainer, I want running MCP servers to see a new ingestion at their next call, so that I never restart Claude Code to get fresh data.
22. As a maintainer, I want `status` to list each repository with its state, snapshot date, issue count and size, plus the data and model directories, so that I know what is ingested and where it lives.
23. As a maintainer, I want a stopped first ingestion reported as stopped, with the command that resumes it, rather than as still running.
24. As a maintainer, I want a repository whose first ingestion has not completed to give no results and say why, rather than results from a random subset of its issues.
25. As a maintainer, I want the tool never to write to GitHub, so that trying it carries no risk to my tracker.
26. As a maintainer, I want to choose the data directory with an environment variable, so that I can keep a large repository on a large disk.
27. As a maintainer, I want the README to say which directories to delete to uninstall, so that I can remove everything.
28. As a maintainer, I want the tool to run on Linux, macOS arm64 and Windows x64, so that it works on the machine I have.
29. As a maintainer, I want a clear message when my Node is too old, rather than an obscure import error.
30. As a maintainer, I want to run the eval on my own repository with a plan of my own, so that I learn how well duplicate search works on my tracker.
31. As a maintainer, I want to rebuild the history from the raw responses already downloaded, so that a parsing fix applies without downloading again.

### Reporters and agents

32. As a contributor about to open an issue, I want to search for duplicates of my draft by title and body, so that I do not file one that already exists.
33. As a contributor, I want to pass the draft's body from a file or from stdin, so that a long body with logs needs no quoting.
34. As an agent in Claude Code, I want `find_duplicates` to declare its output schema and return structured content, so that I parse candidates without scraping text.
35. As an agent, I want an unknown or missing repository to be reported as a tool error listing the ingested ones, so that I can correct my call.
36. As a script author, I want `--json` output with a stable schema and exit codes that tell failure from bad usage, so that I can build on the CLI.
37. As a script author, I want results on stdout and progress, warnings and errors on stderr, so that redirecting the output gives clean JSON.
38. As someone running it from cron or CI, I want progress written as dated lines at most once a minute when there is no terminal, so that logs stay readable.

### People trying the demo

39. As someone judging the project, I want to try it with one `npx` command and no credential of any kind, so that I can see it work in minutes.
40. As someone trying the demo, I want to be told what will be downloaded, from where, and how big it is before it starts, so that I know what I am agreeing to.
41. As someone trying the demo, I want an example search on a real, recent eval case, with the rank its duplicate cluster got in the replay, so that I see both the product in the present and what was measured.
42. As someone trying the demo, I want the headline Recall@5 with its margin and a link to the full report, so that I can judge the numbers.
43. As someone trying the demo, I want the next commands printed, searching by number, by text and the `claude mcp add` line, so that I know what to type.
44. As someone trying the demo, I want to search the demo index from Claude Code with no key, so that I can try the MCP tool too.
45. As someone trying the demo, I want running `demo` again to download nothing, so that it costs nothing to repeat.
46. As someone trying the demo, I want the download verified by its checksum, so that a version of the package always gets the same data.
47. As someone with a real ingestion of godot, I want `demo` to leave it untouched and tell me how to search it.
48. As someone who tried the demo, I want a real ingestion of godot to replace the demo index once it completes, with the demo still searchable meanwhile.
49. As someone running an old version whose demo index was withdrawn, I want a message that tells me how to update.

### Authors and maintainers of the target repository

50. As the author of a godot issue or comment, I want to request its removal through a form that asks only for its URL, so that my text leaves the demo index at its next rebuild.
51. As an author, I want the demo index to carry no logins and no revisions I replaced, so that what I deleted or edited away is not redistributed.
52. As a godot maintainer, I want a NOTICE with the demo index saying where the data comes from, that authors keep their copyright and that the project is not affiliated with Godot.

### Readers of the eval report

53. As a reader of the report, I want every eval case, a duplicate opened since June 2018, replayed at its cutoff with only what existed then, so that the numbers describe what a maintainer would have got when the issue was opened.
54. As a reader, I want a case to count as found when any member of its duplicate cluster opened before the cutoff is in the top 5, because the output leads from any member to the original.
55. As a reader, I want Recall@5 with a 95% margin from a bootstrap over whole duplicate clusters, so that the margins are not narrower than they should be.
56. As a reader, I want Recall@1, @10 and @20, MRR@10 and the distribution of the first cluster member's rank, so that I see more than one cut.
57. As a reader, I want BM25, embeddings and hybrid search compared, with and without the reranker and with and without comment pieces, so that I see what each part contributes.
58. As a reader, I want one row with a strong hosted embedder, so that I see how much quality the keyless default gives up.
59. As a reader, I want GitHub's semantic search as a baseline row with its caveats, so that I can compare with what GitHub offers.
60. As a reader, I want each row's difference against the default with its margin, so that I know which differences are real.
61. As a reader, I want the ladder from a lenient replay that mimics triage-bench to the replay, with each correction's effect and margin, so that I see how much each leak inflates numbers measured the lenient way.
62. As a reader, I want the lenient replay checked against triage-bench's own code on the same data, so that the ladder starts from a faithful imitation.
63. As a reader, I want a column for eval cases opened after the local embedder's release, so that I can see whether training data contaminates the numbers.
64. As a reader, I want the default configuration chosen by a rule stated before the results, so that the choice is not cherry-picked.
65. As a reader, I want each local configuration's p95 latency and peak memory, so that I can weigh quality against speed.
66. As a reader, I want the number of eval cases, the exclusions by reason and the cluster sizes, so that I know what was measured.
67. As a reader, I want the noise of the ground truth estimated by hand review, so that I know how far to trust the extraction and how many correct answers went unrecorded.
68. As a reader, I want the declared limits listed, so that I know what the replay cannot guarantee.
69. As a reader, I want the snapshot date, model revisions, seed and commands, so that I can reproduce the report.

### The author running the eval and the demo

70. As the author, I want the eval to take a snapshot date and give the same numbers after any later ingestion, so that the report stays reproducible while ingestion goes on.
71. As the author, I want to rerun only some rows into an existing results file, so that a change to one configuration does not cost a full run.
72. As the author, I want the results file written after each completed run, so that a crash loses only the run in progress.
73. As the author, I want missing credentials detected before the eval starts, so that a run does not fail hours in.
74. As the author, I want the hosted embedder's vectors cached and its job resumable, so that it fits Voyage's free trial at no cost.
75. As the author, I want GitHub's search responses stored with their date and reused, so that the baseline row is fetched once.
76. As the author, I want reranker scores cached per new issue and piece, so that the six reranked rows do not repeat work.
77. As the author, I want review sheets generated from seeded samples, with no suggested verdict, so that my review is not biased.
78. As the author, I want to re-render the report without searching anything, so that adding verdicts or changing the report is instant.
79. As the author, I want to build the demo index from the latest snapshot with the exclusion list applied, and get its size and sha256, so that I can pin it in the package.
80. As the author, I want a script that publishes the demo index as a release asset without moving the repository's "Latest" release, so that "Latest" keeps pointing at the code.
81. As the author, I want an offline check of each model's ONNX build against its reference model, so that a broken build is caught and the dtype is chosen on evidence.
82. As the author, I want the package published from CI with provenance and no stored npm token, so that each version is traceable to its commit.

### Contributors to this codebase

83. As a contributor, I want every test history built by the real ingestion from a fake GitHub, so that no test can create a history ingestion would never write.
84. As a contributor, I want fake models in process with exact numbers, so that tests pass identically on every platform with no download.
85. As a contributor, I want a CI guard that compares the real models with reference outputs, so that a dependency upgrade that changes vectors or scores fails CI.
86. As a contributor, I want a synthetic repository with leak traps and exact expected numbers, so that any leak into a replay fails a test.
87. As a contributor, I want the packed package tested end to end, so that a file missing from the package or a broken `bin` fails CI.
88. As a contributor, I want to run one test file with `node --test` and no build step.
89. As a contributor, I want CI to run everything on Ubuntu, macOS and Windows on every push, so that platform differences in SQLite, paths and locks show up before merging.

## Implementation Decisions

### Scope

- Phase 1 is duplicate search and its eval. Documentation search and its eval move to phase 2: maintainer closing comments that link the docs are too few for an eval with margins. The data model only leaves room for documentation fragments (§ Pieces).
- The code works on any GitHub repository. Phase 1 is evaluated and demoed on one target repository, **godotengine/godot**: about 5,000 duplicates since June 2018, 64.5k issues and about 285k comments, MIT, no automation that suggests or closes duplicates anywhere in its history, and comment markings by maintainers that can be verified.
- Criteria for choosing a later target repository, in order of weight: medium size (about 14k–65k issues); no duplicate automation that biases the ground truth; comment markings counted only from accounts that show triage-level actions; serving phase 2 only breaks ties.
- Nothing in phase 1 writes to GitHub.

### Runtime, package and platforms

- **TypeScript** (ADR 0001) on **Node, `engines: >=24.15`**: from 24.15.0, `node:sqlite` is a release candidate and prints no experimental warning. Bun and Deno are neither promised nor tested.
- **Platforms promised:** Linux x64 and arm64, macOS arm64, native Windows x64. Intel macOS is not promised.
- **pnpm**, pinned in `packageManager`. Dependency install scripts stay blocked: `allowBuilds: {onnxruntime-node: false, protobufjs: false}`, since onnxruntime-node's script only fetches the CUDA provider on Linux x64 and the CPU binaries are already in its tarball. Transformers.js needs sharp's binary even for text models. `minimumReleaseAge` delays adopting freshly published versions: 7 days, the value the ticket that scaffolds the project picked, with its reason in `pnpm-workspace.yaml`.
- **License:** MIT, covering this repository's own code and docs only.
- **One npm package, `issue-triage-assistant`,** with one `bin` of the same name and one folder per module. Each module exposes a single entry file, and a lint rule forbids importing its internals. No pnpm workspace packages. The core is internal: the public surfaces are the CLI and the MCP tool, and there is no library API and no semver promise beyond them.
- **How TypeScript runs.** Development and tests run the `.ts` sources through Node's type stripping, with no build. The published package is compiled to JS with `tsc`, since Node does not strip types inside `node_modules`. Only erasable syntax (`erasableSyntaxOnly`: no `enum`, `namespace` or parameter properties); relative imports carry `.ts`, which `rewriteRelativeImportExtensions` turns into `.js`. `tsc --noEmit` checks types. The `bin` in `package.json` is `src/bin.ts`, so a clone runs it with no build, and `publishConfig.bin` makes it `dist/bin.js` in the packed package. Only pnpm applies `publishConfig.bin`, so what is published is the tarball `pnpm pack` builds, the one the end-to-end tests run, never a directory published with `npm publish`.
- **The `bin`'s entry file has no imports.** It checks `process.versions.node` first and exits with `issue-triage-assistant needs Node ≥ 24.15; this is Node <v>`, because npm only warns on `engines`.
- **Arguments** are parsed with `parseArgs` from `node:util`, with a hand-written subcommand dispatcher and `--help`, and no CLI dependency.
- **Data from outside is validated at the boundary** (ADR 0001): GitHub responses, model outputs, the offline scripts' files, eval plans and results files.
- **Offline Python** (ADR 0001) lives in `offline/`, one uv project, outside CI. Each script produces a file with a documented format that records the script and inputs that produced it; TypeScript validates that file when it reads it. Nothing the product runs (the CLI, the MCP server, the eval, the demo) imports or launches Python. Phase 1 has two such scripts: the model check (§ Models) and the triage-bench anchor (§ Eval › The ladder and the anchor).

### Modules

Eleven modules in the one package. Every dependency a test replaces enters through the interface: no module creates its own.

| Module | Interface (sketch) | What it hides |
|---|---|---|
| `github` | `createGitHub({baseUrl, token?, sleep})` → GraphQL and REST calls; a call that waits for the quota reports it to the caller's `onWait` | authentication, the quota wait (the reset time against the response's `Date`), retries |
| `history` | `openHistory(file)`: `apply(changes)`, called only by ingestion; `asOf(instant)`: the issues that existed then, streamed one at a time, each with its revisions, comments, timeline events and actors | the history's schema; which items existed at an instant, by their end dates |
| `ingestion` | `ingest({history, github, raw}, {full?, onProgress})` → snapshot date; `reprocess({history, raw})` | the loop by `updatedAt`, the checkpoint, the page sizes, parsing, the merge rules, the raw response archive |
| `markings` | `markingsAsOf(history, instant)` → the original or originals of each marked duplicate, plus the markings set aside, by reason | the signals, the wordings, the maintainer test, the direction, "the marking still stands" |
| `models` | `Embedder` and `Reranker`, each with an id (model, revision, dtype); `cachedEmbedder(embedder, file)` and `cachedReranker(reranker, file)` | Transformers.js (pinned revision, dtype, cache directory), Voyage, the caches' tables |
| `retrieval` | `buildIndex({history, embedders, snapshotDate, scope, kinds, textPrep, window?, exclusions?, results?, onProgress}, file)`; `openIndex(file, {embedders, reranker?})` → `findDuplicates(newIssue, options)`, and each issue's facts and current text by number | deriving pieces (intervals, lost text, backdating, cleaning), the tokenizers, posting lists by start and by end, cumulative arrays, the vectors with their int8 scan and float32 rescoring, the piece of each issue, fusion, reranking |
| `workspace` | `openWorkspace({home, github, models})` → `repositories()`, and `repository(name)`: state, snapshot date, `findDuplicates({issue} \| {title, body}, limit)`, `ingest({full?, onProgress})`, `installDemoIndex(file)`; for `eval` and `demo`, also its history, its vector cache and its `eval/` directory | the data directory and its layout, the per-repository lock, generations and their switch, number → text, the repository states |
| `eval` | `runEval(repository, {snapshotDate, plan, onProgress})` → results file; `reviewSheets(repository, results, seed)`; `renderReport(results, verdicts)` → markdown | § Eval |
| `demo` | `buildDemoIndex(repository, {results, exclusions})` → index file and NOTICE; `fetchDemoIndex({url, sha256}, onProgress)` → verified file | the pinned release tag and sha256, and their override |
| `cli`, `mcp` | thin surfaces over `workspace`, `eval` and `demo` | arguments and output format; one function they share reads the environment and builds the real adapters |

- **Building and searching the index are one module**, because the index format (posting lists by start and by end, cumulative arrays, the vector layout) is the secret both share.
- **`workspace` sits between the core and the surfaces**, so the CLI and the MCP server do not each repeat choosing the repository, its state, resolving a number to text and opening a new generation. `workspace.ingest()` composes the lock, `ingestion.ingest`, `buildIndex` with scope `live`, and the generation switch.
- **Each rule has one owner.** `ingestion` owns how GitHub's responses become changes to the history, end dates included; `history` stores them and answers what existed at an instant; `retrieval` turns revisions into pieces, lost-text rules included.
- **`markings` sits below `retrieval` and `eval`**, so the original a candidate names and the eval's ground truth come from the same rules. Most of godot's duplicates before 2024 were marked by comment, so an original read only from structured fields would name none for them. A wording added after hand review reaches both at once.
- **Long operations report progress through `onProgress`**: pages and issues, quota waits with their length, eval cases and runs, embedded pieces, downloaded bytes. § CLI says how they print.

The core's single entry point, called alike by the CLI, the MCP server and the eval, so what is measured is exactly what users run:

```ts
retrieval.openIndex(file, { embedders, reranker? })  // the adapters by id; tests pass fakes
index.findDuplicates(
  newIssue: { title: string; body: string },  // raw text; the core cleans and prepares it as the index says
  options?: {
    cutoff?: Date;            // replay: only what was visible before it; without one, everything in the index
    statsAt?: Date;           // BM25 statistics instant; defaults to the cutoff, or the index's snapshot date
    config?: RetrievalConfig; // legs (BM25, vectors by embedder id), reranker, comment pieces; when omitted, the one a live index was built for
    exclude?: number;         // the new issue's number, kept out of the candidates
    limit?: number;           // 5 by default, up to 200 issues
  },
): Promise<Candidate[]>
// Candidate: rank, number, score, its piece (kind, id, excerpt),
// and the issue's facts as of the index's snapshot date
```

- **The core never calls GitHub.** Each caller resolves an issue number to text.
- **The score always travels** in `Candidate`, because the eval needs it. The CLI and the MCP server drop it (§ CLI, § MCP server).
- **Up to 200 issues**, because the eval measures Recall@20 and a "not in the top 200" bin. The surfaces cap at 20.

### Ingestion

**One loop, keyed on `updatedAt`.** The first download, resuming a cut-off one, and updating an ingested repository are the same operation.

- An ingestion lists `repository.issues(filterBy: {since}, orderBy: {field: UPDATED_AT, direction: ASC})` from the last snapshot date minus a few minutes, in case the API lags, in pages of 100. `since` is inclusive at whole-second precision and at most 9 godot issues share one second, so a keyset on the last `updatedAt` seen cannot skip or stall.
- It re-fetches each changed issue whole: its title and body with their edit history (`userContentEdits`), its comments with their edit histories, and its timeline, **in pages of 10 issues**, because larger GraphQL pages silently drop timeline items. Reading an issue twice is idempotent.
- The first ingestion is that loop from the beginning. A cut-off one resumes from its checkpoint, the last `updatedAt` it processed.
- There is no separate sweep of comments: creating, editing, deleting or minimizing a comment bumps its issue's `updatedAt`.
- What does not bump `updatedAt` arrives late, with its real date, the next time the issue changes: reactions, cross-references the issue receives, the copy of `marked_as_duplicate` on the original's timeline, mentions, subscriptions and pins, and possibly unmarkings, Projects changes and revisions deleted from an edit history. Phase 1 reads none of them: search reads text, and ground truth reads closes and comments from the duplicate's side. Declared limit.
- **`--full`** runs the same loop from the beginning and merges it into the history, as an escape hatch: about 4 h for godot.

**What the history records.** Issues, comments, every revision of each title, body and comment, and the timeline events: closes and reopens with their reason and `duplicateOf`, duplicate markings and unmarkings, renames, labels added and removed, cross-references and closing pull requests, transfers and comment deletions, each with its date and its actor. Title changes come from rename events; body and comment changes from `userContentEdits`, whose `diff` holds the full text of each revision.

**The history accumulates what it saw.**

- What disappears at the source stays in the history with an end date. It leaves present search and the demo index, and a replay before its end sees it as it existed.
- A comment missing from a re-fetched issue ends at the first comment-deletion event after it was last seen, or at the previous snapshot if there is none. The event carries no comment id, so taking the earliest one keeps the rule that a replay sees less than existed, never more.
- What an author removed reaches neither present search nor the demo index. Only the replay on the eval machine sees it, as with replaced revisions.

**Disappeared issues.** Each ingestion compares `repository.issues.totalCount` (1 point) with the issues alive in the history. When they differ, it lists every issue number (646 points and about 14 min for godot) and ends the missing issues at the last snapshot where the count matched. godot loses about 6.5 issues a month (transferred, deleted or answering 404), and GraphQL answers `NOT_FOUND` for all of them alike.

**Raw responses.** The raw GraphQL responses of each ingestion are kept compressed, locally, beside the history, and are never shipped or committed. `reprocess` rebuilds the history from them, in order, with no network, through the same parsing and merge: a parsing bug is fixed by reprocessing, not by downloading a repository that has changed in the meantime.

**The snapshot date** is the `Date` header of the first response of the last complete ingestion: GitHub's clock, not the local one, so it compares directly with `updatedAt` and `since`. Every change before it that bumps `updatedAt` is captured. A cut-off ingestion does not move it, and the next one starts from it.

**After each ingestion the live index is rebuilt** from the history at the snapshot date, with the same code as the first time, holding only what the default configuration searches (§ Index files). Vectors come from the vector cache, so only new texts are embedded: a day of godot is a few dozen issues, plus their comments if the default searches comment pieces, seconds of CPU. Tokenizing and building the posting lists of the live pieces is estimated, not measured, at 1–3 min for 350k pieces, godot's live issue and comment pieces together, and proportionally less for its ~64k live issue pieces alone.

**Running it.**

- An ingestion runs when someone launches it; a periodic one is scheduled with cron or Task Scheduler, and the README gives the example. A daily ingestion of godot costs about 5–7 points and 15 s.
- A repository becomes searchable when its first ingestion completes. A partial first ingestion is never searched: walked by `updatedAt`, it is an almost random subset.
- When the quota runs out, the ingestion waits for the reset, computed from the reset time against the same response's `Date`, through the `sleep` given to `createGitHub`, and continues.
- A Ctrl+C or a crash leaves the checkpoint, and launching the same command again resumes.
- One ingestion per repository at a time, through the lock of § Workspace. Ingestions of different repositories may run together.
- **The token is `GITHUB_TOKEN`**, required: GraphQL always needs one. It is sent only to github.com, never to an overridden base URL.

### Duplicate markings

`markingsAsOf(history, instant)` decides, at an instant, which issues are marked duplicates and of which original or originals, and which markings are set aside and why. The eval's ground truth and the original each candidate names come from it. The eval passes the snapshot date as the instant (§ Eval › Ground truth).

**Signals.**

1. A `marked_as_duplicate` event not undone later.
2. A close with the duplicate state reason and `duplicateOf`.
3. A maintainer's comment that names an issue of the same repository, not a pull request, with one of the wordings below, followed by the issue's close within 24 h:
   - "duplicate of #N", with whatever follows it;
   - "closing as (a) duplicate (of #N)";
   - "consolidating in #N";
   - "already tracked/reported in #N" and "tracked in #N";
   - "same as #N";
   - "in favor of #N".

- A hedge followed by the close ("possibly a duplicate of #N") counts: the close is the decision.
- The list of wordings grows when hand review (§ Eval › Hand review) finds others. Markings that escape every wording are a declared limit, tens a year as a lower bound.

**Rules.**

- **The marking must still stand at the instant:** the issue is closed, not unmarked, and not reopened and then closed for another reason.
- **The direction comes from the comment's text or from the close's `duplicateOf`, never from the event's fields.** In godot the event appears on both timelines, with `canonical` set to whichever issue owns the timeline. The event only corroborates the date and whether the marking was undone.
- **A maintainer** is an account that took triage-level actions on other people's issues (applying labels, closing them, marking duplicates) at any time in the history as of the instant. The ground truth may know the future of the eval case; only the replay may not. `authorAssociation` is not used: in godot it shows CONTRIBUTOR for verified maintainers and switches for the same person.
- **Bots never count.**
- **Deleted accounts** all collapse into one, so the maintainer test cannot apply. Their marking counts only if a verified maintainer closed the issue.
- **An issue closed as a duplicate by its own author** is set aside, unless the author is a maintainer.
- **A marking that names several issues** joins them all.
- **A marking undone and redone toward another issue:** the last one standing counts.
- **Edges set aside:** an original that is a pull request, lives in another repository (mostly godotengine/godot-proposals), or that the history never saw. An original that disappeared later but that the history holds stays, since it existed at the cutoff.

### Pieces

A piece is the text of an issue (its title and body) or of a comment as it stood between two edits: the unit that duplicate search scores.

**Intervals.** Each distinct state is a piece, valid from when it appeared until the next state replaced it, or until the item disappeared.

- **Pieces are numbered by their start.** At an instant, the visible pieces are the prefix that started before it, minus those that ended before it. ADR 0002's "everything before a cutoff is a prefix" holds as the bound.
- Each piece carries its kind, its start and end, its issue's number and its issue's opening date, and, for a comment, the comment's id.
- **Quick edits are not merged:** merging edits made within minutes would show a text before it was written.
- An edit closes one piece and appends another; items that arrive later with older dates mean renumbering, that is, rebuilding the index, which every ingestion does anyway.

**Kinds.**

- **Issue pieces**: one per state of an issue, its title plus its body.
- **Comment pieces**: one per revision of each human comment, with the comment's text alone: the issue piece already carries the title. The retrieval configuration says whether they are searched.
- **Documentation fragments**: phase 2. A piece's kind and its reference to an issue, which a fragment will not have, leave room for them, and the interval fits a fragment too (valid from the commit that introduced it until the commit that changed it). Phase 1 has no tables for them and does not ingest documentation.
- Timeline events and labels never become pieces or parts of them: events have no text to search, and a new issue has no labels when opened.

**Text preparation.**

- **Cleaning removes only HTML comments**, which do not render and are mostly template instructions repeated across thousands of issues. Code blocks, logs, template headings and system information stay, in raw markdown: error messages and versions are duplicate signals, and BM25's statistics discount repeated headings. The new issue's text is cleaned by the same function.
- **BM25 reads the whole text** of a piece. **The embedder reads its first 512 tokens**, which matches the reranker's cap and the cost the stack was sized on; the tail of long issues is mostly logs and code, which BM25 reads whole.
- The tokenizer for BM25 is our own. The index records its text preparation, tokenizer included, and applies it both to the pieces when building and to the new issue when searching, so the two cannot diverge.

**Lost text and missing content.** A replay may see less than existed, never more.

- A lost intermediate revision extends the previous known text.
- A lost original: the piece starts with the first known text, and before it the issue is invisible to search.
- Edits before about May 2016 leave no trace, so those issues show their current text from their opening. From May 2016 to May 2018 edits have a date but no text. Declared limits.
- Deleted comments, transferred issues and deleted issues no longer have text. Declared limit.
- Bot comments stay in the history and never become pieces.
- Minimized comments are indexed like any other: the API does not say when they were minimized, so excluding them would use moderation from after the cutoff.
- Comments by deleted accounts count as human and are indexed.

### Index files

Every index is a file written once and never changed, in one format for the live index, the eval's indexes, the demo index and the fixture index (ADR 0004). The surfaces read only the index, never the history.

**What an index records:** its snapshot date, its scope, its piece kinds, its text preparation (tokenizer included), the models whose vectors it carries, for a live index the retrieval configuration it was built for, a window of issues by opening date, an exclusion list of issues and comments, and, for a demo or fixture index only, the eval results it carries (§ Demo).

**Per-issue facts**, as of the snapshot date: number, title, URL, opening date, state with its close reason, and its original or originals from `markings`. An issue's current text is its live issue piece. So the CLI and the MCP server resolve a number from the index alone.

**Scopes.**

- **`live`**: the piece valid at the snapshot date of each issue and comment, among the index's piece kinds. It is what `workspace` serves and what a demo index ships. It rejects any cutoff.
- **`full`**: every piece started before the snapshot date, with its end. The replay uses it. It rejects a cutoff after the snapshot date.
- **`backdated`**: each issue's current text as of the snapshot date, as in `live`, with its piece dated at the issue's opening, so the same cutoff prefix selects by opening date. What sets it apart from `live` is the dating, not the text. Steps 0 to 2 of the ladder use it (§ Eval › The ladder and the anchor). It rejects a cutoff after the snapshot date.

**The live index** that `workspace` builds after each ingestion holds only what the default configuration searches: its piece kinds and its embedders' vectors, nothing else, and no vectors at all if the default is BM25 alone. A demo index is then a live index with the exclusion list applied. When the default changes, the next ingestion embeds what the new default needs: for godot, adding comment pieces costs about 4 h of embedding (§ Further Notes).

**A live index is searched with the configuration it was built for**, which it records, not with the package's current default. After an upgrade that changes the default, the current generation keeps serving the previous version's default until the next ingestion writes one built for the new default, as it keeps serving the previous snapshot during any rebuild (§ Workspace); an installed demo index built for an earlier version is the same case, until `demo` installs the one the version pins. Searching the new default over an index built for the old one would find legs or pieces missing, sometimes every leg, as with a granite default over an index built for BM25 alone; refusing would stop every search, the MCP server's included, for as long as the ingestion embeds. `status` and `find-duplicates` say when it happens (§ CLI).

To time each local configuration, the eval builds, under `eval/`, the live index that configuration would get as the default (§ Eval › The default rule).

**Vectors travel with the index.** An index carries the float32 vectors of its pieces in piece order, copied from the vector cache when it is built, and the int8 vectors derived from them. It opens with no vector cache. In godot that is about 0.15 GB per live index when the default searches issue pieces only and 0.7 GB when it also searches comment pieces, and the disk holds two live indexes during a rebuild.

**Sizes, estimated for godot:** a live index of about 250 MB when the default searches issue pieces only and 1–1.5 GB when it also searches comment pieces; int8 vectors in memory of about 25 MB and 135 MB respectively; CLI or MCP server memory of about 50–100 MB and 150–250 MB.

### Retrieval

**Legs.**

- **BM25, scored by our own code** over posting lists in plain `node:sqlite` tables (ADR 0002). Its statistics (the number of visible pieces, each term's count of visible pieces, the average length) are computed as of an instant: the cutoff in a replay, the end of the window in the lenient replay (`statsAt`), the snapshot date outside a replay. Each term has a posting list ordered by start and a second one ordered by end; a term's count at an instant is its postings in the prefix minus those whose piece ended before the instant, and the piece count and average length come from cumulative arrays of starts and ends. Everything is a binary search.
- **BM25's parameters:** k1 = 1.2 and b = 0.75, with Lucene's IDF, `ln(1 + (N − df + 0.5) / (df + 0.5))`, where N is the number of visible pieces and df the term's count of visible pieces; each distinct term of the new issue counts once. They are triage-bench's own (`BM25Retriever` in `src/triage/systems/duplicates.py`, commit `b00f341`), so step 1 of the ladder changes the text preparation and the tokenizer but not the scoring formula. They are constants fixed before the eval runs, never tuned on it (§ Decisions by analogy).
- **Vectors, by an exact scan** written in TypeScript: int8 over the visible prefix, skipping ended pieces through an array of ends. The scan keeps each issue's best score and the 200 best issues, then rescores those issues' best pieces with their float32 vectors. It keeps 200 issues, not 200 pieces, because with comment pieces 200 pieces could collapse into far fewer issues. At 350k pieces the scan took 141 ms with everything visible and 7 ms with 5% visible.

**From pieces to issues.** Each leg keeps the best piece of each issue. After fusion, the issue takes the piece of the leg where it ranks higher, the vector leg's on a tie. That piece gives the excerpt and is the one the reranker scores, so the reader sees what was scored. With one leg, or without comment pieces, it is that leg's best piece.

**Fusion:** reciprocal rank fusion with k = 60. It needs no tuning; calibrating a weighted sum on the eval would leak.

**Reranking:** the reranker reorders the top 20, each pair capped at 512 tokens; from rank 21 on the fusion order stands. A candidate's score is that of the last stage that ordered it: the reranker's in the top 20, the fused score after.

**Candidates.** The new issue's number, when known, is excluded. A candidate's facts are those of the index's snapshot date, in a replay too, where only the ranks matter. Its original is named, never substituted, and may be several.

**The retrieval configuration** says which legs run (BM25, vectors by embedder id), whether the reranker runs, and whether comment pieces are searched. It has a default (§ Default retrieval configuration). The eval sweeps it, always naming the configuration; the surfaces use the one the live index was built for, which is the default once an ingestion has run under the current version (§ Index files).

### Models

**Embedder: granite-embedding-small-english-r2** (48M parameters, 384 dimensions, 8K-token context, Apache-2.0), local, through Transformers.js and `onnxruntime-node`. It is the best small model on the only duplicate benchmark that separates models (CQADupStack-Unix 51.1, against 38.8 for bge-small-en-v1.5).

**Reranker: jina-reranker-v1-turbo-en** (38M, Apache-2.0), local, over the top 20: about 1.8 s per search on the author's laptop. None of the candidate rerankers was trained on duplicates, so the eval decides whether it helps.

**bge-small-en-v1.5 in fp32** is used only by the ladder's anchor (§ Eval › The ladder and the anchor), over the anchor's window.

**voyage-4-large**, hosted, is used only by the eval's two Voyage rows:

- through Voyage's free trial with no card: 200M tokens per model, given once, at 10K tokens a minute;
- on issue pieces only, every revision included: about 133k pieces and 42M tokens, about 3 days in the background, resumable from the vector cache;
- its vectors stay in the author's vector cache: never shipped and never used in CI;
- `VOYAGE_API_KEY` is the author's alone.

**Adapters and caches.**

- `Embedder` and `Reranker` are interfaces, each adapter with an id: model, revision and dtype. The embedder has three adapters (Transformers.js, Voyage, a fake) and the reranker two (Transformers.js, a fake).
- `cachedEmbedder(embedder, file)` is the vector cache: a decorator keyed by the embedder's id and the text, stored in the repository's `vectors.db`. `buildIndex` embeds through it, so a rebuild embeds only new texts. The eval also wraps the embedder it uses for new issues, since a run sends 5,000 of them to Voyage. The surfaces use the bare embedder, so a read never writes.
- `cachedReranker(reranker, file)` is the reranker score cache, keyed by (model, new issue text, piece text) and stored under the repository's `eval/`. Only the eval uses it.

**Downloads.** Models are downloaded anonymously from Hugging Face on first use, pinned to a commit with `revision`, and kept in the platform's cache directory (§ Workspace); CI caches that path. About 400 MB in all with `onnxruntime-node` (granite 52 MB, jina 38 MB).

**The ONNX check**, an offline script:

- It computes reference vectors with sentence-transformers in fp32 on about 1,000 godot pieces and compares them with the product's vectors from Transformers.js in fp32 and in q8, by per-text cosine and by the overlap of each text's 10 nearest neighbours.
- **fp32 must reach a mean cosine ≥ 0.999**; below that the build is broken, and it is investigated or the model changes.
- **q8 is the default dtype** if its 10 nearest neighbours overlap the reference's by ≥ 95%; otherwise fp32. q8 is about twice as fast.
- The same script checks bge-small in fp32, which the anchor depends on, and the reranker, by the Spearman correlation of its scores against the reference.
- It also writes reference vectors for about 20 fixed texts and reference scores for about 20 pairs, with their thresholds, which the CI guard reads (§ Testing Decisions).

### Default retrieval configuration

- **The package's default configuration** is a constant of the package: the one each live index is built for, and so the one the surfaces use once an ingestion has run under that version (§ Index files).
- **Provisional default, until the eval has run:** hybrid BM25 + granite with reciprocal rank fusion, without the reranker and without comment pieces.
- **Final default, set by the rule of § Eval › The default rule.** The rule's choice replaces the provisional default in that constant, and the report marks it together with the rule.
- **The default configuration's run** in a results file is the run whose configuration equals the package's default configuration. `build-demo-index` and the replay line find it that way, not by applying the rule, which also works for CI's single-row run, where the rule cannot be applied. The report warns when the rule's choice differs from the package's default.
- **Every default is local:** no key, no hosted model.

### Workspace

**The data directory** defaults per platform: `$XDG_DATA_HOME/issue-triage-assistant`, `~/Library/Application Support/issue-triage-assistant`, `%LOCALAPPDATA%\issue-triage-assistant\Data`. `ISSUE_TRIAGE_ASSISTANT_HOME` replaces it; there is no flag, so the CLI and an MCP server registered with `claude mcp add -e` never look at different directories. Data never lives in the working directory, which would break `claude mcp add` from any repository.

**Models** go to the platform's cache directory, not the data directory: `$XDG_CACHE_HOME/issue-triage-assistant`, `~/Library/Caches/issue-triage-assistant`, `%LOCALAPPDATA%\issue-triage-assistant\Cache`. They can be downloaded again, and a temporary data directory per test would otherwise download them per test.

**Per repository**, in `repos/<owner>/<repo>/`, lowercased. Each file has one owning module:

| File | Holds | Owner |
|---|---|---|
| `history.db` | the history, written only by an ingestion holding the lock | `history` |
| `vectors.db` | the vector cache | `models` |
| `index-<generation>.db` | the live index of each generation, never changed once written | `retrieval` |
| `state.db` | the current generation, its snapshot date, and whether it is a demo index | `workspace` |
| `lock` | the per-repository lock | `workspace` |
| `raw/` | the compressed raw responses of each ingestion | `ingestion` |
| `eval/` | the eval's indexes, the reranker score cache, the GitHub row's raw responses, and the hand review sheets, which hold the target repository's text and are never committed | `eval` |

**Generations.** A rebuild writes `index-<generation+1>.db` whole, then switches `state.db` in one transaction. On each call, a reader checks `state.db`, opens the new generation when it changed and closes the old one; until then it serves the previous snapshot. Nothing is ever renamed over a file a reader may hold, which Windows refuses. An old generation is deleted once no process holds it; a deletion that fails is retried at the next ingestion.

**The lock** is one the operating system releases when the process dies, such as an exclusive transaction held on the `lock` SQLite file, so a crash or a Ctrl+C never leaves a stale lock. `ingest` waits a few seconds for it before refusing. `find-duplicates`, `status` and the MCP server probe it by trying to take it without waiting and releasing it at once.

**Repository states.**

- **Ready:** a current generation from a real ingestion.
- **Demo index:** a current generation marked as a demo, with no history. It cannot be updated.
- **First ingestion running:** the lock is held and there is no generation yet.
- **First ingestion stopped:** the lock is free, a checkpoint exists, and there is no generation.

While a first ingestion runs or is stopped, the repository gives no results; if a demo index of the same repository is installed, it is searched instead.

**The demo and a real ingestion.**

- `installDemoIndex` refuses when the current generation comes from a real ingestion.
- With a first ingestion in progress, a demo index installs as the current generation; the ingestion fills `history.db` without touching it, and its completion switches to its own generation.
- An `ingest` over an installed demo index replaces it when its first ingestion completes.

**A new issue by number** is resolved from the index (its facts and its live issue piece) or, when the index does not have it, from GitHub over REST, with `GITHUB_TOKEN` when set; unauthenticated suffices for one issue. Either way the issue is excluded from its own candidates.

**The replay line.** When the new issue is given by number, is an eval case, and the index carries eval results (only demo and fixture indexes do), the search also returns the rank its duplicate cluster got in the default configuration's run (§ Default retrieval configuration), which the index carries.

### CLI

**The commands** (contract):

```
issue-triage-assistant ingest [owner/repo ...] [--full]
issue-triage-assistant find-duplicates (<issue> | --title <text> [--body <text> | --body-file <path>]) [--repo owner/repo] [--limit <n>] [--json]
issue-triage-assistant status [--json]
issue-triage-assistant demo
issue-triage-assistant mcp
issue-triage-assistant eval run <owner/repo> --plan <file> [--snapshot <instant>] [--row <id>]...
issue-triage-assistant eval sheets <owner/repo> --plan <file>
issue-triage-assistant eval report --plan <file>
issue-triage-assistant build-demo-index <owner/repo> --results <file> [--exclusions <file>] --out <dir>
issue-triage-assistant reprocess <owner/repo>
```

- `find-duplicates` mirrors `find_duplicates` and `findDuplicates`, and leaves the word `search` free for phase 2's documentation search.
- `mcp` starts the stdio server; it is the word in the `claude mcp add` line.
- `--help` lists every command, with `build-demo-index` and `reprocess` in a "Maintenance" group at the end, and says that the human text may change and scripts should use `--json`. The demo index and GitHub URL overrides stay out of it.
- Publishing a demo index is not a command but a script outside the package (§ Demo).

**The contract.** The command and flag names, the exit codes, and the JSON schema of § Output schema are the contract: breaking them takes a minor version bump and a changelog note. The human text may change in any version. The outputs shown in this section are guidance, not contract.

**Conventions.**

- **stdout carries the result** (candidates, summaries, status) and **stderr the progress, warnings and errors**.
- **Exit codes:** 0 done; 1 failed, including an unknown repository, a first ingestion running or stopped, and a busy lock; 2 bad usage.
- **It never asks anything on stdin**: it runs under MCP, cron and CI. `--body-file -` reads stdin as data.
- **Colour** only on a TTY and without `NO_COLOR`; the output reads the same without it.
- **Times in UTC:** instants as `2026-11-25 09:14 UTC`, opening dates as days.
- **Progress** on stderr: on a TTY, one line rewritten in place, with counts, rate and the time left when the total is known; off a TTY, one line per phase and at most one progress line a minute, each with a UTC timestamp. A quota wait is always a line of its own: `GitHub quota exhausted; waiting 23 min, until 10:05 UTC`. A Ctrl+C during `ingest` ends with `Stopped; run the same command to resume`.
- **Repository states** print as `owner/repo: first ingestion in progress (started 2026-11-26 09:14 UTC); no results until it completes` and `owner/repo: first ingestion stopped after <n> issues; resume it with: issue-triage-assistant ingest owner/repo`. Both exit 1 in `find-duplicates`.

**`find-duplicates`.**

- **The new issue:** a number (`12345` or `#12345`) or an issue URL, which fixes the repository and is an error if it contradicts `--repo`; or a draft, with `--title`, required, and `--body` or `--body-file`, optional.
- **`--repo`** is optional when only one repository is ingested. When it is missing or unknown, the error lists the ingested ones.
- **A number not in the index** is fetched from GitHub, and the output says so.
- **A live index built for an earlier version's default** is searched with its own configuration (§ Index files), and one line on stderr says so: `owner/repo: searched with the default configuration of an earlier version; the next ingest applies this version's` (`demo` instead of `ingest` for a demo index). The exit code stays 0.
- **`--limit`:** 5 by default, up to 20.
- **No score in any output**, `--json` included: an uncalibrated number reads as confidence to a human as much as to an agent running the CLI. Only the eval sees it.
- **Errors:** `#N is a pull request`; `#N not found in owner/repo (transferred or deleted?)`.
- **Human output** (guidance):

  ```
  $ issue-triage-assistant find-duplicates 4512
  example/widgets · snapshot 2026-11-25 09:14 UTC · issues opened later are not candidates
  New issue #4512: Slider jumps to 0 when dragged past the end

   1. #3988  Slider value resets when the pointer leaves the track
      open · opened 2025-03-02
      https://github.com/example/widgets/issues/3988
      issue    "Dragging the slider handle beyond the right edge sets the value to the minimum instead of…"

   2. #4102  Slider wraps to min on overshoot
      closed (duplicate) · duplicate of #3988 · opened 2025-06-17
      https://github.com/example/widgets/issues/4102
      comment  "Same here on 2.3. It only happens when the pointer is released outside the window…"
               https://github.com/example/widgets/issues/4102#issuecomment-1234567890
   3. …
  ```

  - The new issue line has two more forms: `New issue #4630 (opened after the snapshot; text fetched from GitHub): …` and `New issue (draft): …`.
  - State and original print apart: the original comes from `markings`, not from the close reason, so a `closed (completed)` issue may be `duplicate of #N`. Several originals print as `duplicate of #N, #M`.
  - The replay line, when it applies, follows the candidates: `Replay: when #4512 was opened (2026-08-02), the default configuration ranked a member of its duplicate cluster 3rd.`, or `… no member of its duplicate cluster was in the default configuration's top 200.` The results hold the first member's rank, not which issue it was, so the line cannot name it.

**`ingest`.**

- `ingest owner/repo` runs the first ingestion and every later one. It takes several repositories. With no argument it ingests every ingested repository except demo indexes, one after another: that is the cron line.
- `--full` is the escape hatch of § Ingestion.
- Without `GITHUB_TOKEN` it fails before any request and suggests `GITHUB_TOKEN=$(gh auth token)`. Under `ISSUE_TRIAGE_ASSISTANT_GITHUB_URL` it asks for none. It never reads `GH_TOKEN` or `gh auth token` itself.
- Over a demo index, one line says the demo stays searchable until this first ingestion completes and is then replaced.
- A busy lock prints `owner/repo: another ingestion is running` and exits 1. With several repositories it goes on with the others and ends with a summary of the failures and exit 1.
- **Summary per repository, on stdout** (guidance):

  ```
  $ issue-triage-assistant ingest
  example/widgets: snapshot 2026-11-26 09:14 UTC (previous 2026-11-25 09:13 UTC)
    47 issues changed (9 new) · 35 comments added or edited · 1 comment deleted · 0 issues disappeared
    61 pieces embedded · 7 GitHub points · 15 s
  ```

  After a first ingestion, the changes line is `first ingestion complete: <n> issues, <n> comments`.

**`status`** lists the data directory, the models directory with its size, and each repository with its state, snapshot date, issue count and size, noting when its live index was built for an earlier version's default configuration; `--json` gives the same. There is no `remove` in phase 1: it would need the lock, and on Windows it would fail while an MCP server holds the index. The README's "Uninstall" section lists the data directory, the models' cache and npx's cache.

```
$ issue-triage-assistant status
Data:   /home/u/.local/share/issue-triage-assistant
Models: /home/u/.cache/issue-triage-assistant (412 MB)

example/widgets    ready        snapshot 2026-11-26 09:14 UTC   14,203 issues   1.9 GB
godotengine/godot  demo index   snapshot <date> UTC             64,401 issues   312 MB
```

**`demo`**: § Demo.

**`mcp`** serves `find_duplicates` over stdio, with stdout reserved for the protocol. With stdin on a TTY no client is attached, so it writes to stderr that it is a stdio server meant to be launched by an MCP client, with the `claude mcp add` line, and exits 2.

**The eval commands**: § Eval › Running the eval.

**`build-demo-index`** and **`reprocess`**: § Demo and § Ingestion. `reprocess` takes the lock, rebuilds the history from `raw/` into a new file with no network, builds the live index as a new generation, and prints the counts and the snapshot date, which does not move. It refuses on a demo index, which has no `raw/`.

**`npx` for the demo, a global install for real use.** npm documents no default staleness check for `npx`'s cached packages, so an `npx` line in cron or in `claude mcp add` may run an old version indefinitely. The demo uses `npx issue-triage-assistant …` and `claude mcp add issue-triage-assistant -- npx -y issue-triage-assistant mcp`. For ingestion, cron and MCP, the README installs globally with `npm install -g issue-triage-assistant`, then `claude mcp add issue-triage-assistant -- issue-triage-assistant mcp`; its cron example uses the absolute path and reads `GITHUB_TOKEN` from a file.

### MCP server

- **Transport and SDK:** stdio only, launched by an MCP client; HTTP would need authentication. The reference TypeScript SDK, its version chosen by the ticket that implements the server.
- **One read-only tool, `find_duplicates`,** over every ingested repository. The server never ingests, never writes to GitHub and never writes to the data directory.
- **Input:** `repository`, optional when only one is ingested; the new issue by number (`issue`) or, for a draft, by `title` and `body`; `limit`, 5 by default and up to 20. With a number, the text comes from the index or, when the index does not have the issue, from GitHub.
- **No cutoff:** the tool searches the present. An optional `as_of` can be added later without breaking anything; serving it would mean serving a `full` index.
- **Output:** the schema of § Output schema, declared as the tool's `outputSchema`, returned as `structuredContent` and, as the MCP specification recommends, also as serialized JSON in a text block. The human rendering is the CLI's only. No score.
- **Errors:** an unknown or missing repository (listing the ingested ones), a first ingestion running or stopped, a pull request, an issue not found: results with `isError: true` carrying the CLI's messages.
- A running server sees a new generation at its next call.
- It searches with the configuration the live index was built for, as the CLI does (§ Index files). Its output does not flag a live index built for an earlier version's default: `status` and the CLI report it.

### Output schema

One JSON schema for `find-duplicates --json` and `find_duplicates`, in snake_case (contract):

```json
{
  "repository": "example/widgets",
  "snapshot_date": "2026-11-25T09:14:03Z",
  "new_issue": { "number": 4512, "title": "…", "source": "index" },
  "candidates": [{
    "rank": 1, "number": 3988, "title": "…", "url": "…",
    "opened_at": "2025-03-02T10:21:44Z",
    "state": "closed", "close_reason": "duplicate",
    "duplicate_of": [3412],
    "excerpt": { "kind": "comment", "text": "…", "url": "…#issuecomment-1234567890" }
  }],
  "replay": { "cutoff": "2026-08-02T14:31:00Z", "rank": 3 }
}
```

- `source` is `index`, `github` or `draft`; a draft has no `number`.
- `close_reason` is `completed`, `not_planned`, `duplicate` or `null`.
- `duplicate_of` is a list, empty when the issue is not a marked duplicate.
- `replay` appears only when the replay line applies (§ Workspace), with `rank: null` when no member was in the top 200.
- **The excerpt** is the first ~300 characters of the piece, whitespace collapsed, cut at a word boundary and ended with `…`. For an issue piece it is the start of the body, without the title, which is already a field. A comment excerpt carries the comment's URL.

### Eval

The eval runs only on the author's machine, against an ingested repository. CI runs its harness on the synthetic repository (§ Testing Decisions); no godot data goes to CI.

#### Ground truth

- **An eval case is a duplicate.** Its ground truth is every member of its duplicate cluster opened before its cutoff: its original, that original's own original, and the other duplicates of any of them. An eval case exists only if at least one member was opened before the cutoff. Clusters are built on `markingsAsOf` at the snapshot date.
- A case counts as **found at k** when any member of its ground truth is in the top k. `find_duplicates` names the original of a candidate that is itself a duplicate, so reaching any member leads to the original in one step.
- **Edge cases:** an original newer than its duplicate keeps the case only through another, older member, and is otherwise out and counted; the newer original never becomes an eval case itself; an issue in the middle of a chain is an eval case if it has an earlier member, and a member of the ground truth for the others.
- triage-bench's ground truth (the original plus earlier duplicates of the same original) is a subset of the cluster; the lenient replay uses it.

#### Eval cases

- **Every duplicate opened from 2018-06-01**, when the text at a cutoff becomes guaranteed, **up to 90 days before the snapshot date** is an eval case, with no sampling, unless it is out and counted below: about 5,000 duplicates in godot. The 90 days let markings settle (the historical p90 marking delay is 83 days).
- **Candidates come from the whole history before the cutoff**, issues from before 2018 included, with their declared limits.
- **Out and counted:** a case with no member opened before its cutoff; a case whose text at opening is lost (about 1%), since its first known text would be a leak in its favour; markings set aside by `markings`.
- **Late markings are in**, with no cap: a perfect system would have found the original when the issue was opened.
- **Cases opened since 2026-06-18**, when GitHub's filing-time suggestions arrived, are in with no stratum of their own: nothing records whether a reporter was shown suggestions.
- **No non-duplicates.** Phase 1 measures retrieval. Precision at the real duplicate rate needs a threshold that decides "this is a duplicate", which is confidence, and confidence belongs to phase 2.

#### Metrics and margins

- **Primary: Recall@5.**
- **Also:** Recall@1, @10 and @20 (@20 bounds what the reranker can do); MRR@10, which the anchor needs; the distribution of the first member's rank: median, histogram, and "not in the top 200".
- **Margins:** 95% percentile bootstrap, 10,000 resamples, fixed seed, **resampling whole duplicate clusters**: 63% of godot's duplicates share their original with another, so the cases of a cluster are not independent.
- **Two configurations on the same cases:** the 95% interval of the paired difference, using the same resamples for both. "Within the margin" means that interval contains 0.

#### The main table

The replay over every eval case: `full` index, text at opening, our ground truth, BM25 statistics at each cutoff. 15 rows:

- **12 local configurations:** {BM25, granite, hybrid with RRF k = 60} × {with or without the reranker over the top 20} × {with or without comment pieces}. All are candidates for the default rule.
- **2 voyage-4-large rows:** alone, and in hybrid with BM25. Issue pieces only and no reranker, paired with the same granite configurations without comment pieces.
- **1 GitHub semantic search row:** `search_type=semantic`, the closest to the issue form's suggestions; the query is the title plus the body at opening, trimmed to stay under 2,000 characters, with `repo:<owner/repo> is:issue created:<cutoff`; the top 20 are kept; raw responses are stored with their date under `eval/` and reused. It needs `GITHUB_TOKEN` and is limited to 10 requests a minute (about 8.5 h for godot). Its caveats go with the row: GitHub's index holds current text, a leak in its favour, so the comparison is conservative; it measures GitHub's search, not necessarily the engine behind the issue form's suggestions; and its index changes over time.
- **Recent stratum:** a secondary column for cases opened since 2025-09-01, the first full month after granite-embedding-small-english-r2's release (2025-08-15), about 330 cases with a snapshot at the end of November 2026, more with later ones, with the same date for every row. For voyage-4-large, released in 2026, it does not rule out contamination, and the report says so.
- **Latency and memory** are measured for the 12 local configurations only (§ The default rule). The hosted rows, both voyage-4-large rows and the GitHub row, show "—": they can never be the default, and their latency would measure the provider's network and quota, not the system.
- **No hold-out:** the knobs are fixed in advance (RRF k = 60, no weights, fixed cleaning, fixed BM25 parameters), so choosing among configurations barely overfits.

#### The ladder and the anchor

A cumulative ladder from a lenient replay that mimics triage-bench to the replay, showing how much each correction moves the numbers.

- **Window:** test period 2025-09-01 to 2026-08-31, candidates from 2024-09-01, both fixed in the plan so a later run stays comparable: 231 cases with our ground truth, fewer with triage-bench's extraction.
- **Rows:** BM25, embeddings, and hybrid with RRF. No reranker and no comment pieces: triage-bench indexes no comments.
- **The lenient replay's knobs live where they cannot touch the path the product uses:** candidates within the window are the index's window, so BM25 statistics count only the window, as in triage-bench; triage-bench's text preparation and tokenizer are the index's text preparation; bge-small is a model whose vectors the index carries; BM25 statistics at the window's end are `statsAt` on the entry point, its only knob.

| Step | What changes | Index | Run |
|---|---|---|---|
| 0 | Imitation: the anchor | `backdated`, window, triage-bench's text preparation and tokenizer, bge-small fp32 | triage-bench's ground truth and extraction, current text, `statsAt` = the window's end |
| 1 | Our system: a bridge, not a correction | `backdated`, window, our preparation and tokenizer, granite | the same |
| 2 | Correction: BM25 statistics at the cutoff | the same | no `statsAt` |
| 3 | Correction: text at the cutoff | `full`, window | text at opening |
| 4 | Correction: our ground truth (maintainers only, the cluster) | the same | our ground truth |
| 5 | Correction: the whole history as candidates | `full` over the whole history | |

- triage-bench's text preparation, as read from its code: the title twice plus the body cut at 2,000 characters for BM25, and the title plus the first 1,500 body characters for embeddings. Its extraction reads `MarkedAsDuplicateEvent` (cancelled by unmarking) with the direction inferred, and "Duplicate of #N" comments, full URLs included; it drops pairs whose original is newer, resolves no chain, and does not exclude bots.
- **Step 1 is a bridge:** the corrections are measured on what ships, and bge-small never embeds the whole history.
- **The paired steps (2, 3) go first**, while the case set is the anchor's, so their margins are clean.
- **Steps 4 and 5 change the case set** and are measured decomposed: the paired effect on the cases common to both sides, with its interval, and how many cases enter and leave, with their Recall@5 apart.
- **The anchor.** An offline script runs triage-bench's own code (MIT) on the same window, with data downloaded the same day, using BM25 and bge-small-en-v1.5; its results file, recording the script and inputs, is what step 0 is compared against. The anchor holds when both get the same eval cases, with any differing pair listed and explained, and each system's Recall@5 and MRR@10 differ by less than the margin of the measurement itself. Exact equality is not expected: triage-bench tokenizes with scikit-learn, and the same model gives slightly different numbers through ONNX in TypeScript.
- **If the anchor fails,** one ticket investigates it within a time cap, its findings go into the report, the corrections are still measured from our lenient replay, and the comparison with triage-bench moves to prose.

#### The default rule

- **The default is the configuration with the best Recall@5 on the full replay** among those that need no key and run under ~5 s per search at p95. The hosted rows can never be the default.
- **Ties within the margin** go to the lowest p95 latency; latencies within 10% of each other go to the one with less peak memory. So BM25 alone, tying hybrid, would win, which also spares the model download.
- **Each local configuration is timed, and its memory measured, on the live index it would get as the default**, outside a replay, since that is what a user would run: an index of scope `live` at the snapshot date holding exactly what that configuration searches (§ Index files), built by the eval under the repository's `eval/` from the vector cache. That is up to 6 shapes, {BM25, granite, hybrid} × {with or without comment pieces}; the reranker does not change the index.
- **Latency** is timed on the author's laptop, with the text at opening of 200 eval cases as new issues, after warm-up, timing the whole search (embedding the new issue, searching and reranking), with a monotonic clock.
- **Memory** is the peak RSS of a fresh process per local configuration that opens that index and runs the 200 latency searches. The results file records it per local row beside the p95 latency, so `renderReport` applies the rule from the results file alone.
- **The hosted rows have neither**, and show "—" (§ The main table).

#### Hand review

- **Sample A, extraction:** 50 eval cases, stratified between comment markings and duplicate closes. For each: is it the right original, in the right direction, marked by a maintainer, and the same problem? Reported as a precision with its Wilson interval.
- **Sample B, undercount:** 50 cases the default did not find in its top 5. For each: is any of its 5 candidates also an unrecorded duplicate? Reported as a corrected band for Recall@5.
- **The human reviews** on sheets the eval prepares (links, the marking comment, both texts at the cutoff), with no suggested verdict: about 3–4 h.
- **No eval case is fixed by hand**, for reproducibility. A systematic error changes the extraction rule, and the eval runs again.

#### Running the eval

**The plan** is a JSON file: the runs by id (the main table's rows and the ladder's steps), the window, the seed, the sample sizes, and paths, relative to the plan, to the anchor's results and to the verdicts file. JSON rather than TypeScript, because a user's plan loads under `npx`. godot's plan lives in `docs/eval/`, beside its results.

**A run** fixes its case set (which ground truth, the window or the whole history), its index, its configuration, its `statsAt`, and the new issue's text: at opening, or current as of the snapshot date. The eval reads both texts from the history; the core cleans and prepares them.

**Internal seams:**

1. **Ground truth:** `extractGroundTruth(history, snapshotDate)` → eval cases with their clusters, plus case exclusions by reason. triage-bench's ground truth is a second function of the same shape, with its own extraction.
2. **The run:** eval cases × runs → the results file. The eval's indexes are files under the repository's `eval/`, rebuilt when their parameters change; their vectors come from the cache, so a rebuild costs minutes of tokenizing.
3. **The report:** `renderReport(results, verdicts)` → markdown, pure: the metrics, the seeded cluster bootstrap, the paired differences, the default rule and the ladder. The results file is the seam between running and reporting, so redoing the report searches nothing.
4. **Hand review:** `reviewSheets` writes sheets A and B from seeded samples.
5. **The reranker score cache** (§ Models).

**The results file** holds, as numbers only (no text and no logins): per case and run, the first member's rank up to 200; each case's issue number, cutoff and cluster; the top 5 of each case under the default configuration, which sample B needs; the exclusions by reason; the p95 latency and peak memory of each local row, and no latency or memory for the hosted rows; the configurations, model revisions, snapshot date and seed; and the package version that computed each run.

**`eval run <owner/repo> --plan <file> [--snapshot <instant>] [--row <id>]...`**

- Writes `results.json` and `report.md` in the plan's directory.
- **`--snapshot`** defaults to the latest snapshot date and is never later than it. The eval reads the history, the pieces, the candidates and the ground truth as of it, and gives the same numbers after any later ingestion.
- **`--row`**, repeatable, runs only those runs. Into a results file with the same snapshot date and seed, it replaces them and keeps the rest; with another snapshot date, it refuses. With no results file it starts a new one, which is how CI runs the default's row alone to build the fixture index.
- **The results file is rewritten atomically after each completed run**, so a crash loses only the run in progress.
- **Credentials are checked before starting:** a missing `GITHUB_TOKEN` or `VOYAGE_API_KEY` for any selected run fails and names those runs.
- **At the end** it renders `report.md` and prints each run's Recall@5 with its interval, the default marked, and the paths written (guidance):

  ```
  Snapshot 2026-11-25 09:14 UTC · 1,204 eval cases · seed 20261125
  row             Recall@5  95% CI
  bm25            0.xx      0.xx–0.xx
  hybrid-rerank   0.xx      0.xx–0.xx   ← default
  …
  Wrote eval/results.json and eval/report.md
  ```

**`eval sheets <owner/repo> --plan <file>`** writes sheets A and B, one Markdown file per sample, under the repository's `eval/`, never committed since they hold text, and prints their paths. When the verdicts file the plan names does not exist, it writes a CSV template there (sample, case number, one empty column per question), which is committed: it holds issue numbers and verdicts only.

**`eval report --plan <file>`** renders `report.md` from the results, the verdicts and the anchor's results, searching nothing and opening no repository. With no verdicts, § 5 of the report says "pending hand review". Verdicts for cases that no longer match the current samples are flagged in the report, left out, and warned about on stderr.

#### The report

Markdown generated from the results file, in `docs/eval/` beside it, linked from the README. Its sections:

1. **Main table:** the 15 rows with Recall@1/5/10/20 and MRR@10, each with its interval, the recent stratum column, the p95 latency and peak memory, and the default marked together with the rule that chose it. The hosted rows show "—" for latency and memory, with the reason: they can never be the default, and their latency would measure the provider's network and quota, not the system. When the rule's choice differs from the package's default configuration, the report warns.
2. **Paired differences** of each row against the default.
3. **The ladder:** the steps × the 3 rows, each step's effect with its interval, the decomposition of steps 4 and 5, and the anchor's verdict.
4. **Eval cases:** the count, exclusions by reason, cluster sizes, and the histogram of the first member's rank.
5. **Ground truth noise:** samples A and B.
6. **Declared limits:** text before 2016 and from 2016 to 2018; deleted content; what does not bump `updatedAt`; what pretrained models learned in training, which is outside "only what existed"; GitHub's index holding current text; markings that escape every wording.
7. **Reproduction:** the snapshot date, model revisions, seed, package versions when they differ, and commands. The GitHub row needs a token and the Voyage rows a key, so neither is reproducible without them.

### Demo

**What it shows:** duplicate search in the present, over a ready-built **demo index** of godot, by number or by text, from the CLI and from `find_duplicates`, plus the replay line for eval cases. It neither replays an eval case nor reproduces the main table: replaying needs every revision, which would redistribute text its authors removed, and the table needs the history, hours of CPU and two credentials; § Reproduction of the report covers it.

**No credential of any kind:** neither model keys nor a GitHub token. `GITHUB_TOKEN` is used when set, only to fetch by number an issue the demo index lacks, which also works unauthenticated.

**What the demo index holds.**

- The live index's pieces, with their posting lists and vectors: a demo index is a live index with the exclusion list applied, so it holds only what the default configuration searches (§ Index files). Comment pieces only if the default searches them (about 250 MB without them, 1–1.5 GB with them), and no vectors and no model download if the default is BM25 alone.
- Per issue, only what the output shows: number, title, URL, opening date, state with its close reason, and its original as a derived fact, without who marked it.
- The eval results it carries: each eval case's rank under the default, and the headline Recall@5 with its margin. `demo` and the replay line read them from the installed index, not from `docs/eval/`, which does not exist under `npx`.
- No logins, timeline events, replaced revisions, raw responses or Voyage vectors.
- **Text as is,** @mentions included: every piece carries its issue's URL, so masking would be undone with a click, and a naive mask would eat GDScript annotations such as `@export` or `@onready`, which are duplicate signals.

**Building it.**

- **`build-demo-index <owner/repo> --results <file> [--exclusions <file>] --out <dir>`** builds the index file and the NOTICE in `<dir>` from the latest snapshot. It prints their sizes and sha256, the snapshot date, and how many issues and comments the exclusion list removed. It takes the ranks and the headline Recall@5 the index carries from the default configuration's run, the run whose configuration equals the package's default configuration (§ Default retrieval configuration), so it works on CI's single-row run too. It refuses when the results lack that run, and on a demo index, which has no history.
- **When:** right after an ingestion, when the eval takes a new snapshot (in practice the two coincide) and on a removal request; no fixed cadence. Built from the latest snapshot, a rebuild also drops whatever was deleted, edited away or disappeared since.
- **Before publishing,** the author downloads it from the release, checks the checksum and runs a search. The godot demo index never goes through CI: its example search would print godot text in public Actions logs.

**Hosting and pinning.**

- **An asset of a GitHub release of this repository,** one release per demo index, tagged `demo-index-<date>` and created with `--latest=false`, so "Latest" keeps pointing at the code. A script in `scripts/`, outside the package, publishes it; the author pastes the tag and sha256 into `demo`'s constants.
- **Each package version pins the tag and its sha256**, and `demo` checks the checksum, so a version always gets the same data. A rebuild ships as a patch release; an older version whose demo index is no longer published fails with a message asking to update.
- **The CI override:** `ISSUE_TRIAGE_ASSISTANT_DEMO_INDEX_URL` and `ISSUE_TRIAGE_ASSISTANT_DEMO_INDEX_SHA256`, set together, replace the pinned values, so CI points `demo` at the fixture index. Documented for contributors, not in `--help`.

**Notice and removal.**

- **A NOTICE travels with the download** and `demo` names it in one line. It gives the source and the snapshot date, says that each author keeps their copyright and that the project is not affiliated with Godot, carries godot's MIT notice in case it applies, and explains how to ask for a removal.
- **The removal channel is an issue form** in this repository that asks only for the URL of the issue or comment. No email.
- **An exclusion list committed to the repository**, of issue numbers and comment ids, is applied by every rebuild.
- **The eval keeps measuring on the whole history:** it redistributes no text, and excluding would move its numbers with every request.
- **If the whole set has to be withdrawn,** at the request of godot's maintainers for instance, the demo falls back to the synthetic fixture, and real use to `ingest` with a token.

**The `demo` command.**

- It says what it will download, from where and how big (the size from the response, before its body is read), then downloads without asking: the command is the consent.
- It verifies the checksum and installs the demo index as an ingested repository marked as a demo (§ Workspace).
- It runs one example search on the most recent eval case in the carried results, whatever its outcome, so the replay line shows too.
- It prints the headline Recall@5 with its margin and a link to the report at the package version's tag, the NOTICE line with the removal form, and the next commands.

  ```
  $ npx issue-triage-assistant demo
  Demo index of godotengine/godot, snapshot <date> UTC: <size> MB from
    https://github.com/jmbaquerosanchez/issue-triage-assistant/releases/download/demo-index-<date>/…
  The first search also downloads the models (~400 MB) to <cache directory>.
  [progress on stderr]
  Checksum OK. Installed as godotengine/godot.

  Example: the most recent eval case.
  <the find-duplicates output for #<N>, with its replay line>

  Eval: Recall@5 0.xx (95% CI 0.xx–0.xx) over <n> eval cases replayed at their cutoffs.
    Report: https://github.com/jmbaquerosanchez/issue-triage-assistant/blob/v<version>/docs/eval/report.md
  Issue text belongs to its authors; see NOTICE (<path>). To request a removal: <form URL>

  Next:
    npx issue-triage-assistant find-duplicates <number>
    npx issue-triage-assistant find-duplicates --title "…" --body "…"
    claude mcp add issue-triage-assistant -- npx -y issue-triage-assistant mcp
  ```

  (guidance) The models line shows only if the default uses models.
- **Run again**, it downloads nothing: the header becomes `Demo index already installed (snapshot …); checksum OK.` and the rest repeats.
- **Over a real ingestion** it downloads nothing, prints `godotengine/godot is already ingested (snapshot …); search it with:` and the next commands, and exits 0.
- **A version whose demo index is no longer published** asks to update with `npm install -g issue-triage-assistant@latest` or `npx --prefer-online issue-triage-assistant@latest demo`.
- **Requirements:** Node ≥ 24.15 on the promised platforms, about 400 MB of models and `onnxruntime-node`, plus the demo index.

### Environment variables

| Variable | Read by | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | `ingest` (required), number → text (optional), the eval's GitHub row (required) | sent only to github.com, never to an overridden base URL |
| `VOYAGE_API_KEY` | the eval's Voyage rows | the author's alone |
| `ISSUE_TRIAGE_ASSISTANT_HOME` | every command and the MCP server | replaces the data directory |
| `ISSUE_TRIAGE_ASSISTANT_GITHUB_URL` | the `github` client | the fake's base URL in tests, with REST at the base and GraphQL at `<base>/graphql` |
| `ISSUE_TRIAGE_ASSISTANT_DEMO_INDEX_URL`, `ISSUE_TRIAGE_ASSISTANT_DEMO_INDEX_SHA256` | `demo` | set together, they replace the pinned demo index |
| `NO_COLOR` | the CLI | disables colour |

`GITHUB_API_URL` is not read: Actions sets it for itself and GitHub Enterprise users set it for other tools, so reading it would point this tool at a host it does not promise. `GH_TOKEN` is not read either. One function shared by `cli` and `mcp` reads the environment and builds the real adapters.

### Publishing and CI

- **CI runs everything on Ubuntu, macOS and Windows on every push,** caching the models' directory on each platform. It assumes a public repository, where standard runners are free.
- **The package goes to the public npm registry** (not GitHub Packages, which needs a token even to install), from CI on a `v*` tag, with npm trusted publishing, so no npm token is stored, and with provenance. Versions are 0.x. The workflow fires on `v*` tags only, never on `demo-index-*`. The first publish and the npm account are the human's.
- **The repository is public before the ticket that scaffolds the project** (a human task, [Make the repository public](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/35)): the anonymous demo download, the removal form, provenance, free CI on three platforms and protecting `main` all need it.

## Testing Decisions

### What makes a good test

- A test checks external behaviour at an agreed seam (§ Test seams): what `findDuplicates` returns, what an ingestion leaves in the history as read back through `asOf`, what a command prints and exits with. Never private functions, table layouts or call order.
- Expected numbers are exact wherever the inputs are under the test's control: ranks, recall, bootstrap intervals with a fixed seed, scores from the fake models. Latency is never asserted.
- Every test that needs a history builds it through the real ingestion; no test writes the history, an index or a results file by another path, except hand-written results files for the report's pure tests.

### Doubles

- **GitHub, faked at HTTP** (ADR 0003). The `github` client takes a base URL. Tests run a local fake HTTP server that serves a synthetic repository as it stood at an instant the test sets, answering the client's few queries by operation name: it is not a GraphQL engine and does not check the query text, which the author's real ingestions check. The same fake serves the in-process tests and the subprocess ones (the MCP server fetching an issue not ingested, building the fixture index, and the `demo` flow, for which it also serves the fixture index). The snapshot date comes from the fake's `Date` header, so tests set the fake's instant instead of injecting a clock, and the quota wait goes through an injected `sleep`. The fake does not imitate GitHub's quirks; the page size covers the dropped timeline items.
- **GitHub's real shape still runs in CI:** ingestion's tests parse responses recorded from this repository's own tracker, which is public and holds only its own text.
- **Scenarios.** The fixture language is a scenario of changes, typed TypeScript modules in `test/support/`: an issue opened, renamed or with its body edited; a comment added, edited, deleted or minimized; labels; a close with its reason and `duplicateOf`; a duplicate marking; an issue transferred or gone. Each change carries its date and its actor, an account; what kind of account it is comes out of the scenario, as in godot (a maintainer is an account seen triaging other people's issues, the author is relative to each issue, third parties may have no permissions, and bots and the deleted-account ghost are accounts GitHub marks as such). A `historyFrom(scenario)` helper runs the real ingestion against the in-process fake.
- **Models, fake in process:** an embedder by term hashing and a reranker by term overlap, deterministic, with no download and no float noise across platforms. Fakes are injected in process only: the published binary cannot select them. The caches are decorators over any adapter, so tests count the fake's calls.
- **Real models** run only in the CI guard and in the end-to-end tests, whose fixture is designed with wide margins so ranks do not depend on the platform. Voyage has no CI test.
- **SQLite has no port** and is real everywhere, on temporary files.
- **The environment:** tests call `openWorkspace` with doubles; end-to-end tests set `ISSUE_TRIAGE_ASSISTANT_HOME` to a temporary directory per test, `ISSUE_TRIAGE_ASSISTANT_GITHUB_URL`, and the two demo index variables.

### The synthetic repository

One shared scenario serves the eval's harness, ingestion's end-to-end cases and the fixture index; edge-case tests write their own short scenarios. It holds invented issues, comments, edits and markings, with no third-party text.

- **Leak traps for the replay:** a candidate renamed after the cutoff; a comment added later; a term that only appears later, for BM25 statistics; an original newer than its duplicate; a chain.
- **Ingestion cases:** two ingestions, at T1 and then at T2, give the same live index as one at T2; an ingestion cut off and resumed gives the same history as an uninterrupted one, and the cut-off one does not move the snapshot date; an issue that disappears makes the count mismatch, leaves the live index, and ends at the last snapshot that matched; a deleted comment ends at its event's date, and a replay before that date still sees it; an `updatedAt` tie at a page boundary loses nothing; a running MCP server sees a new ingestion at its next call; a second concurrent ingestion of the same repository is refused.

### Runner and layout

- **`node:test` with `node:assert`,** run on the `.ts` sources through Node's type stripping, with no build or transform.
- **Unit and seam tests** live next to their module, in `src/<module>/*.test.ts`. Fakes, scenarios, recorded responses, reference outputs and helpers live in `test/support/`; end-to-end tests in `test/e2e/`.
- **End-to-end tests run the packed package:** after the build and `pnpm pack`, the tarball runs as `npx` would.
- **The fixture index is built by the packed package**, as the author builds a demo index: `ingest` of the synthetic repository from the fake, `eval run` with the default's row only, and `build-demo-index`, with real models. The fake then serves the file to `demo`. It is never committed.
- **The CI guard** embeds the ~20 fixed texts with the real embedder and checks the cosine against the reference vectors, and checks the real reranker's order on the ~20 reference pairs, with the thresholds the offline script wrote. A Transformers.js or onnxruntime upgrade that changes the outputs fails CI with no Python.

### Test seams

For the ticket that scaffolds the project to copy to § Test seams of `docs/agents/flow.md`. "Doubles" means the fake models, the fake GitHub, the scenarios and the recorded responses, all in `test/support/`.

| Seam | What is tested there | Tests and doubles | Command for one file |
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

### Prior art

- The first tests, from the ticket that scaffolds the project, run the bin in a subprocess: `src/cli/cli.test.ts` from the sources and `test/e2e/package.test.ts` from the packed package, both through `test/support/run-cli.ts`. The scripts under `docs/research/` are evidence of their reports, not tests.
- triage-bench's `tests/test_leakage.py` checks its time mask for BM25 and difflib only. The synthetic repository's leak traps go further: the vector leg, text revisions, comments and BM25 statistics.
- ADR 0003 (GitHub faked at HTTP) and ADR 0004 (immutable index files) record the decisions this section rests on.

## Out of Scope

From the map, product-wide:

- A bot that acts on its own, without a maintainer's approval: the product proposes and a maintainer decides.
- A generic chat over the documentation: the core is deciding, acting with permissions, and measuring it.
- Several users with authentication: it is a local tool.

From the map, beyond this map:

- Fine-tuning an embedder on duplicates from before the cutoff: it needs a time split that shrinks the eval cases, training in Python and one model per repository, and reopens redistribution if the model ships; it only makes sense once the eval exists to measure it.
- A second target repository, to check whether the numbers hold beyond godot (microsoft/terminal was the cheap candidate: 14k issues, markings by event or `/dup`, suggestion bots between 2023-11 and 2025-09): phase 1 is evaluated and demoed on one target repository, so it is a fresh effort once phase 1's eval exists.

From the map, later phases, each with its own map:

- The triage agent: categories, confidence and escalation policy, replies that cite their sources, and the claim verifier (phase 2).
- Documentation search and its eval (phase 2): too little ground truth in phase 1 for an eval with margins.
- Choosing an agent framework (phase 2).
- The MCP write tools, their permission levels and the approval queue (phase 3).
- The minimal interface, its review screen, and the GitHub Action (phase 4).

Also out of phase 1:

- Any write to GitHub, from any surface.
- Measuring precision at the real duplicate rate, a threshold that decides "this is a duplicate", or any score shown to users: that is confidence, phase 2's.
- An `as_of` on `find_duplicates`, and replays from the MCP tool.
- Ingesting or searching documentation fragments; the data model only leaves room for them.
- Reading what does not bump an issue's `updatedAt` (reactions, received cross-references, the original's copy of a duplicate marking, mentions, pins).
- A watch mode or daemon, and `find_duplicates` ingesting on its own.
- An HTTP transport for the MCP server.
- A public library API.
- A `remove` command.
- Bun, Deno and Intel macOS.
- Eval rows with a 2,048-token embedding cap, difflib, GitHub's `hybrid` search, or bge-small outside the ladder (the first can be added later).
- A stratum for duplicates filed since GitHub's filing-time suggestions arrived (2026-06-18).
- A hold-out set.
- Any godot data in CI, including a fixed subset of eval cases.
- Replaying an eval case or reproducing the main table from the demo.
- Masking @mentions or logins inside issue text in the demo index.
- A hosted reranker.

## Further Notes

- **The map:** [Map: phase-1 spec for duplicate search and its eval](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/2).
- **ADRs:** 0001 (TypeScript, offline Python in `offline/`), 0002 (own BM25 and vector scan over plain SQLite), 0003 (GitHub faked at HTTP, every test history built by the real ingestion), 0004 (every index an immutable file, the surfaces read only the index).
- **Research reports** behind the decisions, in `docs/research/`: target repository candidates, the GitHub API for history, redistribution, existing triage tools, embedding and reranking models, hybrid search stores, and the retrieval stack facts.
- **Where each section comes from:**

| Section | Tickets |
|---|---|
| Scope | [Target repository and phase 1 scope](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/9), [Target repository candidates and their ground truth counts](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/3), [Duplicate search as an MCP read tool or as a library](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/11), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43) |
| Runtime, package and platforms | [Runtime, package manager and repository license](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/10), [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Phase 1 CLI surface](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/36), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43) |
| Modules | [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Duplicate search as an MCP read tool or as a library](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/11), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43), [Searching a live index built for an older default configuration](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/45) |
| Ingestion | [Incremental ingestion](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/32), [GitHub API for ingesting a repository's history under a cutoff](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/4), [Data model and chunking under a cutoff](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/13), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Phase 1 CLI surface](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/36), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43) |
| Duplicate markings | [Duplicate eval strategy](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/14), [Target repository and phase 1 scope](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/9), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43) |
| Pieces | [Data model and chunking under a cutoff](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/13), [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27) |
| Index files, Retrieval | [Data model and chunking under a cutoff](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/13), [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43), [Searching a live index built for an older default configuration](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/45) |
| Models | [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Embedding and reranking models usable from TypeScript](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/7), [Data model and chunking under a cutoff](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/13) |
| Default retrieval configuration | [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Duplicate eval strategy](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/14), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43), [Searching a live index built for an older default configuration](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/45) |
| Workspace | [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Incremental ingestion](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/32), [Phase 1 CLI surface](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/36), [Phase 1 demo mode](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/15), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43) |
| CLI, MCP server, Output schema | [Phase 1 CLI surface](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/36), [Duplicate search as an MCP read tool or as a library](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/11), [Searching a live index built for an older default configuration](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/45) |
| Eval | [Duplicate eval strategy](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/14), [Where phase 1 differs from triage-bench and GitHub's duplicate suggestions](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/21), [Existing AI triage and duplicate detection tools](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/6), [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Incremental ingestion](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/32), [Phase 1 CLI surface](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/36), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43) |
| Demo | [Phase 1 demo mode](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/15), [Whether issue text and derived data can be redistributed](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/5), [Incremental ingestion](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/32), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Phase 1 CLI surface](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/36), [Close the gaps found reviewing the phase 1 spec](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/43) |
| Environment variables | [Phase 1 CLI surface](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/36), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Phase 1 demo mode](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/15) |
| Publishing and CI | [Phase 1 demo mode](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/15), [Runtime, package manager and repository license](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/10), [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27) |
| Testing Decisions | [Phase 1 modules and seams](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/27), [Duplicate eval strategy](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/14), [Incremental ingestion](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/32), [Phase 1 demo mode](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/15), [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12), [Searching a live index built for an older default configuration](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/45) |

- **Left to the ticket that scaffolds the project:** § Verification of `docs/agents/flow.md` and copying § Test seams there; `tsconfig` with `erasableSyntaxOnly` and `rewriteRelativeImportExtensions`; the lint tool and its rule against importing a module's internals; pnpm with `allowBuilds`, `packageManager` and `minimumReleaseAge`, whose value it picks; the Node check in the `bin`'s entry file and `parseArgs`; the CI matrix on three platforms with the models' cache path; the npm publishing workflow on `v*` tags.
- **Cost, estimated on the author's laptop (i7-1255U) for godot:**

| Item | Cost |
|---|---|
| First ingestion (full pass) | ~4 h, ~7,800 GitHub points |
| Daily ingestion | ~15 s, ~5–7 points |
| Embedding the live index's pieces once, granite q8 | ~2.6 h if the default searches issue pieces only, ~6.5 h if it also searches comment pieces, none if it is BM25 alone |
| Embedding every revision once, for the replay | ~5.5 h issues only, ~11 h with comments |
| voyage-4-large row | ~3 days in the background, $0 |
| One replay configuration without the reranker, ~5k cases | ~25 min |
| Reranker over the 6 configurations that use it | up to ~15 h, less with the score cache |
| GitHub row | ~8.5 h in the background |
| Hand review | ~3–4 h of human time |
| A search, without / with the reranker | < 0.5 s / +~1.8 s |
| Money | $0 |

- **The weakest figures:** our own BM25 and the size of its posting lists were not measured; CPU hours come from one laptop with ±25% noise; rebuilding the live index after an ingestion is estimated at 1–3 min with comment pieces; Voyage may use the submitted texts to train its models (they are public anyway).

## Decisions by analogy

What a branch resolves by analogy with something already decided, with the decision it follows.

- **BM25's parameters are fixed before the eval runs and never tuned on it** (§ Retrieval). Follows the "knobs fixed in advance" of [Duplicate eval strategy](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/14) (RRF k = 60, no weights, fixed cleaning), which is why the eval needs no hold-out (§ Eval › The main table).
- **A live index is searched with the configuration it was built for**, until the next ingestion builds one for the package's current default (§ Index files), resolving [Searching a live index built for an older default configuration](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/45). Follows the generations of § Workspace: a reader keeps serving the previous snapshot until the new generation is written, so a generation is served as it was built.
