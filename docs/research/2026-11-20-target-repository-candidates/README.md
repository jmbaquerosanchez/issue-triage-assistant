> Snapshot of 2026-11-20 for [Target repository candidates and their ground truth counts](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/3). Not updated: later research supersedes it.

# Target repository candidates and their ground truth counts

Research for ticket #3 of the phase-1 map (#2). It gathers facts; the target repository is chosen in #9.

**Question.** Which open source repositories on GitHub could be the target repository for phase 1, and how much ground truth does each one offer? For each candidate: duplicates marked by a maintainer (not by a bot), closing comments that link to the documentation, issues closed by a pull request, total issues, whether the documentation lives in the repository, license, and how widely known it is. The bar is a few hundred usable duplicates (300 eval cases give about ±4.5 points on an 80% hit rate).

## Answer in short

- **The bar is cleared, by a wide margin and by many candidates.** 29 well-known repositories were sampled (1,300 issues, 40 to 48 each). In 28 of them the lower bound of the 95% interval for usable duplicates is above 300; the exception is vercel/next.js (about 320, interval 187–507).
- **Largest pools of usable duplicates** (maintainer-marked, original named explicitly, original opened earlier, same repository): microsoft/vscode (about 18,600), microsoft/PowerToys (about 12,900), flutter/flutter (about 6,000), godotengine/godot (about 5,000), microsoft/terminal (about 3,600), llvm/llvm-project (about 3,400, 11 of its 24 usable sampled issues imported from Bugzilla), then a group between 1,100 and 2,500 (golang/go, microsoft/TypeScript, oven-sh/bun, dotnet/runtime, dart-lang/sdk, home-assistant/core, rust-lang/rust, dotnet/roslyn, mui/material-ui, openai/codex, python/cpython, zed-industries/zed, angular/angular, nextcloud/server). anthropics/claude-code also estimates about 5,000, but with a wide interval (2,340–9,634) and from the minority of its duplicates that people marked.
- **Bot markings are rare, except in a few recent cases.** In anthropics/claude-code, 26 of the 40 sampled duplicates were marked only by a bot (an automated duplicate finder that comments, waits and closes). In oven-sh/bun, 7 of 41 (an automation account and a GitHub Actions workflow, both from 2025–2026). In every other sampled repository, 0 to 2 per sample. Several repositories run bots that *suggest* duplicates before a maintainer decides; that is not a bot marking, but it can bias the ground truth (see Caveats).
- **Naming the original is the limiting factor, not the volume of markings.** A duplicate label alone does not say which issue is the original. Repositories whose maintainers mark through `Duplicate of #N` comments, slash commands or GitHub's "Close as duplicate" name it explicitly; where they only apply a label (microsoft/TypeScript, spring-projects/spring-boot, microsoft/WSL), a large share of the originals can only be inferred from a nearby `#N` mention.
- **Imported histories hold more ground truth than the counts show**: llvm/llvm-project (Bugzilla), python/cpython (bugs.python.org) and golang/go (Google Code) carry pre-GitHub duplicate markings in imported text, only partly reached by this method.

## Method

All data comes from GitHub's own APIs, read with the authenticated `gh` CLI on 2026-11-20, read-only. The scripts are in [`scripts/`](scripts/) next to this note, and their aggregated outputs in [`scripts/out/`](scripts/out/) (raw timelines with comment bodies are not committed).

### What counts as a duplicate marking

GitHub records duplicates in four ways, and the ticket names three of them:

1. **The `marked_as_duplicate` timeline event**, created when someone types "Duplicate of" followed by an issue number in a new comment; it only appears if that person has write access to the repository ([GitHub Docs: Marking issues or pull requests as a duplicate](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/marking-issues-or-pull-requests-as-a-duplicate); [Issue event types: `marked_as_duplicate`](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types#marked_as_duplicate)).
2. **A duplicate label**, whose name each repository chooses (`*duplicate`, `Resolution-Duplicate`, `r: duplicate`, `status: duplicate`...). Applying labels needs triage access ([GitHub Docs: Managing labels](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels): "Anyone with triage access to a repository can apply and dismiss labels").
3. **A "Duplicate of #N" comment** that does not create the event, because its author lacks write access (common in godotengine/godot, kubernetes/kubernetes, dotnet/runtime, angular/angular, nextcloud/server and rust-lang/rust, see the second table under Results; for example microsoft/vscode#35347, where an organization member's `Duplicate of #32746` produced no event) or because it is phrased differently ("Closing as duplicate of #N").
4. **GitHub's "Close as duplicate"**, which sets the issue's close reason to `DUPLICATE` (GraphQL enum `IssueClosedStateReason`: `COMPLETED`, `NOT_PLANNED`, `DUPLICATE`, read by schema introspection; [GitHub Docs: Issue status webhooks and workflows](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/issue-status-webhooks-and-workflows): "closing it as a duplicate sets Duplicate"). It is recent: in microsoft/vscode no issue closed before 2024 carries it, 30 closed in 2024 do, and 4,561 closed since 2025 (searches by `closed:` date range). The search qualifier `reason:duplicate` works although the search docs only list `reason:completed` and `reason:"not planned"` ([Searching issues and pull requests](https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests#search-by-the-reason-an-issue-was-closed)): in microsoft/vscode, `reason:completed` + `reason:"not planned"` + `reason:duplicate` = 185,219 + 51,129 + 4,591 = 240,939, exactly the number of closed issues.

### Steps

1. **Candidates** ([`repos.txt`](scripts/repos.txt)): 86 well-known, actively maintained repositories with thousands of issues, in any language. For each, GraphQL `repository` gives stars, forks, license (`licenseInfo.spdxId`), issue count and every label whose name contains "dup" with its issue count ([`01_repo_metadata.py`](scripts/01_repo_metadata.py)).
2. **Search counts** ([`02_counts.py`](scripts/02_counts.py)), all with `is:issue`: closed issues; `reason:duplicate`; `"duplicate of" in:comments`; closed issues with `linked:pr` (issues linked to a pull request by a closing reference, [Searching issues: linked](https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests#search-for-linked-issues-and-pull-requests)); closed issues whose comments contain the repository's docs URL prefix; and the **frame**, the union `(label:<dup labels> OR reason:duplicate OR "duplicate of" in:comments)`. Boolean `OR` only works with GraphQL `search(type: ISSUE_ADVANCED)` (with `type: ISSUE` the same query returns 0) or REST with `advanced_search=true`.
3. **Sampling** ([`03_sample.py`](scripts/03_sample.py), [`shortlist.txt`](scripts/shortlist.txt)): for the 23 candidates with the largest frames plus 6 more well-known ones, 40 issues from the frame, allocated across creation years in proportion to the frame's size per year, drawn from random start dates inside each year (two consecutive issues by creation date per draw, `sort:created-asc`), seeded. For each issue, its labeled/unlabeled, marked/unmarked as duplicate, closed, reopened events and its comments.
4. **Classification** ([`04_classify.py`](scripts/04_classify.py)) of each sampled issue:
   - *Marking events*: a duplicate label that was not removed later, a `marked_as_duplicate` event not undone, or a last close with reason `DUPLICATE`.
   - *Who decided*: a human account, or a bot acting on a maintainer's slash command posted within the hour before (`/dup #574` in microsoft/terminal#3517, executed by a since-deleted bot account; `/duplicate #130688` in microsoft/vscode#130736, executed by `vscode-triage-bot`; `/triage duplicate` and `/close` with Prow's `k8s-ci-robot` in kubernetes/kubernetes), or a bot reacting to a trigger label a human applied (`bot/duplicate` in grafana/grafana#49918). Those count as the maintainer's marking. A "Close as duplicate" by the issue's own author does not count, since anyone can close an issue they opened ([GitHub Docs: Closing an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/closing-an-issue)).
   - *Bots*: actor type `Bot` (GitHub Apps), or a login matching automation patterns (`-bot`, `bot$`, `robot`, `github-actions`, `policy-service`, ...), plus automation accounts found by auditing every marking actor with two or more markings in the sample ([`actors.py`](scripts/actors.py)): `robobun` (oven-sh/bun) is an ordinary user account that, on 2026-08-15, closed several of the sampled issues (years old) as duplicates within about 15 minutes, each with a long explanatory comment (for example oven-sh/bun#8439).
   - *Maintainer comment only*: no marking event, but a comment by an `OWNER`, `MEMBER` or `COLLABORATOR` that says "duplicate of #N" (the ticket's third signal).
   - *Imported*: the line `*** This bug has been marked as a duplicate of bug llvm/llvm-project#N ***` that LLVM's Bugzilla migration kept in imported comments (llvm/llvm-project#27285).
   - *The original*: **explicit** when the `marked_as_duplicate` event, the close's `duplicateOf` or a "duplicate of #N" / `/dup #N` text by the decider or a maintainer names it; **inferred** when it is the last same-repository `#N` in a comment by the decider or a maintainer up to a day after the marking.
   - *Usable* (the headline): marked by a maintainer (event, comment or imported), explicit original, in the same repository, opened before the duplicate, and not a pull request. "+ inferred" also accepts inferred originals.
5. **Estimates**: usable ≈ frame × the sample's usable share, with a Wilson 95% interval on the share.
6. **Checks**: docs-link closing comments on 12 candidates ([`05_docs_sample.py`](scripts/05_docs_sample.py)), and the sampled timelines of two issues per repository compared with REST ([`06_verify_rest.py`](scripts/06_verify_rest.py)).

### How the findings of #4 were handled

The GitHub API research ([#4's report](https://github.com/jmbaquerosanchez/issue-triage-assistant/blob/research/github-api-history/docs/research/github-api-history.md)) flagged three traps; this note meets each one:

- **Actor type `Bot` only covers GitHub Apps.** Bots were also detected by login patterns and by auditing the marking actors per repository, which found `robobun`; `vscodenpa`, `vscode-triage-bot`, `k8s-ci-robot` and `grafanabot` are user accounts (type `User`) that the patterns catch. Deleted accounts (shown as `ghost`, `null` in GraphQL) were treated like bots unless a maintainer's command preceded them: in microsoft/terminal they turned out to be the retired bot that executed `/dup` commands.
- **Two duplicate mechanisms.** The classifier reads both, `marked_as_duplicate` events and `stateReason: DUPLICATE` with `duplicateOf`, plus labels and comments. The swap of `canonical` and `duplicate` was observed here too: on golang/go#50099, whose comment says "Duplicate of #40785", GraphQL returns `canonical` = 50099 and `duplicate` = 40785, the reverse of the schema descriptions ("canonical: The authoritative issue or pull request which has been duplicated by another"). The event appears only on the duplicate's timeline (golang/go#40785 has none). So the original is taken as whichever side is not the issue itself.
- **Large GraphQL pages drop timeline items.** Pages were kept small (2 issues per search, up to 100 timeline items each), and for 46 sampled issues (the longest sampled timeline and one random issue per repository, up to 91 items) the counts per event type matched the REST timeline endpoint exactly ([`06_verify_rest.json`](scripts/out/06_verify_rest.json); [REST: Timeline events](https://docs.github.com/en/rest/issues/timeline)).

## Results

Columns: *Stars* and *Issues* (issues only, pull requests excluded) from GraphQL `repository`; *License* is GitHub's detected SPDX id (`NOASSERTION`: GitHub could not match one license; `none`: no license detected); *Frame* is the union search of step 2; *n* the sampled issues (a few more than 40 where draws returned two issues); *Usable* the estimate and 95% interval of step 5; *Closed by a PR* the `is:closed linked:pr` count; *Docs-link comments* the closed issues whose comments contain the docs prefix, with, where sampled, how many of the sampled hits had a maintainer's comment with the link in the 24 hours before the close; *Docs in the repo* from the repository's root contents and the existence of a separate website repository (both via the REST contents and repository endpoints). The rows are ordered by the lower bound of the usable interval.

### Sampled candidates

| Repository | Stars | Issues | License | Frame | n | Usable, explicit original (95% CI) | + inferred original | Marked only by a bot (in sample) | Closed by a PR | Docs-link comments (proxy) | Docs in the repo |
|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---|
| microsoft/vscode | 196k | 259,522 | MIT | 42,796 | 46 | **~18,607** (12,928–24,716) | ~26,050 | 1/46 | 22,011 | 3,251 (3/20 maintainer closing) | no (microsoft/vscode-docs) |
| microsoft/PowerToys | 141k | 42,631 | MIT | 16,530 | 46 | **~12,937** (10,650–14,503) | ~14,015 | 0/46 | 1,397 | 382 (4/14 maintainer closing) | no (`doc/` = dev docs, specs) |
| flutter/flutter | 181k | 117,154 | BSD-3-Clause | 12,651 | 44 | **~6,038** (4,270–7,852) | ~8,626 | 0/44 | 17,945 | 957 (6/17 maintainer closing) | no (flutter/website; `docs/` = contributor docs) |
| godotengine/godot | 120k | 64,497 | MIT | 7,128 | 46 | **~4,959** (3,934–5,768) | ~4,959 | 0/46 | 17,751 | 1,374 (7/20 maintainer closing) | partly (class reference in `doc/`; manual in godot-docs) |
| microsoft/terminal | 105k | 14,229 | MIT | 4,336 | 44 | **~3,646** (3,063–3,992) | ~4,040 | 0/44 | 2,562 | 90 (1/12 maintainer closing) | no (MicrosoftDocs/terminal) |
| llvm/llvm-project | 42k | 102,702 | NOASSERTION | 6,873 | 48 | **~3,436** (2,501–4,372) | ~3,723 | 0/48 | 13,300 | 826 (1/16 maintainer closing) | yes (`llvm/docs`, `clang/docs`, ...) |
| anthropics/claude-code | 156k | 107,949 | none | 33,137 | 40 | **~4,971** (2,340–9,634) | ~4,971 | 26/40 | 2,694 | 342 | no (product source and docs not in repo) |
| oven-sh/bun | 97k | 19,381 | NOASSERTION | 3,461 | 41 | **~2,279** (1,750–2,715) | ~2,279 | 7/41 | 5,049 | 208 (3/18 maintainer closing) | yes (`docs/`) |
| golang/go | 140k | 74,756 | BSD-3-Clause | 4,915 | 48 | **~2,253** (1,601–2,935) | ~2,253 | 0/48 | 1,842 | 1,452 (7/20 maintainer closing) | partly (`doc/` = spec, release notes; site in golang/website) |
| dotnet/runtime | 18k | 74,859 | MIT | 3,714 | 44 | **~2,110** (1,568–2,612) | ~2,110 | 0/44 | 17,472 | 1,123 (4/19 maintainer closing) | no (dotnet/docs, dotnet-api-docs; `docs/` = design) |
| microsoft/TypeScript | 112k | 43,883 | Apache-2.0 | 7,765 | 48 | **~2,427** (1,549–3,520) | ~4,691 | 0/48 | 6,273 | 657 (0/18 maintainer closing) | no (microsoft/TypeScript-Website) |
| home-assistant/core | 92k | 76,640 | Apache-2.0 | 3,723 | 46 | **~2,023** (1,496–2,526) | ~2,104 | 0/46 | 17,942 | 5,179 (2/20 maintainer closing) | no (home-assistant/home-assistant.io) |
| dart-lang/sdk | 11k | 62,718 | BSD-3-Clause | 4,374 | 46 | **~2,092** (1,493–2,706) | ~2,377 | 1/46 | 734 | 423 | no (dart-lang/site-www; `docs/` = contributor) |
| dotnet/roslyn | 21k | 37,009 | MIT | 2,754 | 46 | **~1,796** (1,398–2,129) | ~1,976 | 0/46 | 6,698 | 82 (1/12 maintainer closing) | no (user docs in dotnet/docs; `docs/` = compiler notes) |
| mui/material-ui | 99k | 20,631 | MIT | 2,263 | 44 | **~1,646** (1,316–1,893) | ~1,749 | 0/44 | 3,762 | 1,218 | yes (`docs/`) |
| rust-lang/rust | 122k | 64,731 | Apache-2.0 | 4,433 | 46 | **~1,831** (1,254–2,467) | ~1,831 | 0/46 | 17,774 | 1,805 | partly (`src/doc`; std docs in source; the Book is rust-lang/book) |
| openai/codex | 136k | 41,610 | Apache-2.0 | 3,591 | 40 | **~1,436** (946–1,990) | ~1,436 | 0/40 | 891 | 53 | yes (`docs/`) |
| nextcloud/server | 38k | 21,901 | AGPL-3.0 | 1,976 | 44 | **~1,123** (834–1,389) | ~1,168 | 0/44 | 3,558 | 1,036 | no (nextcloud/documentation) |
| python/cpython | 78k | 79,353 | NOASSERTION | 3,766 | 44 | **~1,284** (824–1,840) | ~1,369 | 0/44 | 2,049 | 7,577 | yes (`Doc/`) |
| angular/angular | 101k | 31,168 | MIT | 2,613 | 48 | **~1,143** (802–1,508) | ~1,143 | 0/48 | 5,144 | 486 | yes (`adev/` = angular.dev) |
| zed-industries/zed | 95k | 23,786 | NOASSERTION | 3,314 | 44 | **~1,205** (788–1,695) | ~1,205 | 0/44 | 5,832 | 601 | yes (`docs/`) |
| pandas-dev/pandas | 51k | 28,704 | BSD-3-Clause | 1,725 | 47 | **~844** (608–1,083) | ~1,248 | 0/47 | 12,181 | 1,801 | yes (`doc/`) |
| dotnet/aspnetcore | 39k | 40,435 | MIT | 2,147 | 42 | **~869** (581–1,192) | ~1,074 | 0/42 | 3,725 | 852 | no (dotnet/AspNetCore.Docs; `docs/` = contributor) |
| grafana/grafana | 78k | 46,006 | AGPL-3.0 | 2,125 | 48 | **~708** (461–1,009) | ~974 | 1/48 | 12,557 | 1,209 | yes (`docs/sources`) |
| microsoft/WSL | 34k | 12,780 | MIT | 1,683 | 45 | **~673** (455–918) | ~1,159 | 2/45 | 95 | 282 | no (MicrosoftDocs/wsl) |
| spring-projects/spring-boot | 82k | 44,020 | Apache-2.0 | 2,278 | 48 | **~712** (454–1,033) | ~1,281 | 0/48 | 742 | 400 | yes (`documentation/`) |
| pytorch/pytorch | 106k | 62,846 | NOASSERTION | 1,321 | 42 | **~535** (357–733) | ~535 | 0/42 | 10,880 | 1,138 | yes, API reference (`docs/source`) |
| kubernetes/kubernetes | 129k | 50,063 | Apache-2.0 | 1,214 | 41 | **~503** (337–688) | ~563 | 0/41 | 11,894 | 2,337 | no (kubernetes/website) |
| vercel/next.js | 144k | 25,799 | MIT | 1,285 | 44 | **~321** (187–507) | ~350 | 0/44 | 4,810 | 1,752 | yes (`docs/`) |

### How each sampled issue was marked

Each sampled issue falls in one column, by the rules of step 4. *Not marked* means the issue is in the frame only through comment text: most often an original whose thread says another issue is a "duplicate of" it, or a reporter's or bot's guess. The last column counts, among the issues marked by people (the first three columns), how their original was found.

| Repository | Maintainer event | Maintainer comment only | Imported | Bot only | Author self-close | Deleted account | Not marked | Original named explicitly / inferred / none |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| microsoft/vscode | 35 | 2 | 0 | 1 | 0 | 0 | 8 | 23 / 11 / 3 |
| microsoft/PowerToys | 41 | 3 | 0 | 0 | 1 | 0 | 1 | 37 / 4 / 3 |
| flutter/flutter | 31 | 1 | 0 | 0 | 0 | 0 | 12 | 23 / 9 / 0 |
| godotengine/godot | 13 | 23 | 0 | 0 | 1 | 0 | 9 | 36 / 0 / 0 |
| microsoft/terminal | 43 | 0 | 0 | 0 | 0 | 0 | 1 | 38 / 4 / 1 |
| llvm/llvm-project | 18 | 0 | 11 | 0 | 0 | 0 | 19 | 25 / 2 / 2 |
| anthropics/claude-code | 6 | 0 | 0 | 26 | 3 | 1 | 4 | 6 / 0 / 0 |
| oven-sh/bun | 28 | 2 | 0 | 7 | 0 | 0 | 4 | 30 / 0 / 0 |
| golang/go | 26 | 2 | 0 | 0 | 2 | 0 | 18 | 27 / 0 / 1 |
| dotnet/runtime | 13 | 15 | 0 | 0 | 4 | 0 | 12 | 28 / 0 / 0 |
| microsoft/TypeScript | 31 | 1 | 0 | 0 | 0 | 2 | 14 | 17 / 14 / 1 |
| home-assistant/core | 21 | 9 | 0 | 0 | 1 | 0 | 15 | 28 / 1 / 1 |
| dart-lang/sdk | 27 | 5 | 0 | 1 | 2 | 0 | 11 | 27 / 3 / 2 |
| dotnet/roslyn | 35 | 3 | 0 | 0 | 1 | 0 | 7 | 34 / 3 / 1 |
| mui/material-ui | 38 | 4 | 0 | 0 | 0 | 0 | 2 | 33 / 3 / 6 |
| rust-lang/rust | 11 | 11 | 0 | 0 | 0 | 0 | 24 | 22 / 0 / 0 |
| openai/codex | 20 | 1 | 0 | 0 | 7 | 0 | 12 | 21 / 0 / 0 |
| nextcloud/server | 17 | 14 | 0 | 0 | 0 | 0 | 13 | 30 / 1 / 0 |
| python/cpython | 17 | 6 | 0 | 0 | 2 | 0 | 19 | 22 / 1 / 0 |
| angular/angular | 12 | 15 | 0 | 0 | 1 | 0 | 20 | 27 / 0 / 0 |
| zed-industries/zed | 17 | 1 | 0 | 0 | 2 | 0 | 24 | 18 / 0 / 0 |
| pandas-dev/pandas | 24 | 10 | 0 | 0 | 0 | 0 | 13 | 23 / 11 / 0 |
| dotnet/aspnetcore | 35 | 4 | 0 | 0 | 1 | 0 | 2 | 26 / 8 / 5 |
| grafana/grafana | 27 | 3 | 0 | 1 | 0 | 0 | 17 | 20 / 7 / 3 |
| microsoft/WSL | 35 | 1 | 0 | 2 | 1 | 0 | 6 | 20 / 13 / 3 |
| spring-projects/spring-boot | 40 | 4 | 0 | 0 | 0 | 0 | 4 | 21 / 17 / 6 |
| pytorch/pytorch | 16 | 7 | 0 | 0 | 2 | 0 | 17 | 23 / 0 / 0 |
| kubernetes/kubernetes | 4 | 20 | 0 | 0 | 0 | 0 | 17 | 21 / 2 / 1 |
| vercel/next.js | 10 | 9 | 0 | 0 | 1 | 0 | 24 | 18 / 1 / 0 |

### All candidates: search counts

| Repository | Stars | Issues | License | Duplicate label(s): issues | `reason:duplicate` | `"duplicate of"` in comments | Frame (union) | Closed, linked PR | Docs-link comments (prefix) |
|---|---:|---:|---|---|---:|---:|---:|---:|---|
| microsoft/vscode | 196k | 259,522 | MIT | `duplicate`: 383, `*duplicate`: 30,242 | 4,591 | 24,060 | 42,796 | 22,011 | 3,251 (`code.visualstudio.com/docs`) |
| anthropics/claude-code | 156k | 107,949 | none | `duplicate`: 27,461 | 23,165 | 25,648 | 33,137 | 2,694 | 342 (`docs.anthropic.com`) |
| microsoft/PowerToys | 141k | 42,631 | MIT | `duplicate`: 792, `Resolution-Duplicate`: 13,585 | 1,584 | 15,092 | 16,530 | 1,397 | 382 (`learn.microsoft.com`) |
| flutter/flutter | 181k | 117,154 | BSD-3-Clause | `r: duplicate`: 7,628 | 1,561 | 9,336 | 12,651 | 17,945 | 957 (`docs.flutter.dev`) |
| microsoft/TypeScript | 112k | 43,883 | Apache-2.0 | `Duplicate`: 5,860 | 58 | 5,484 | 7,765 | 6,273 | 657 (`www.typescriptlang.org/docs`) |
| godotengine/godot | 120k | 64,497 | MIT | — | 815 | 7,058 | 7,128 | 17,751 | 1,374 (`docs.godotengine.org`) |
| llvm/llvm-project | 42k | 102,702 | NOASSERTION | `duplicate`: 4,397 | 1,060 | 6,162 | 6,873 | 13,300 | 826 (`llvm.org/docs`) |
| golang/go | 140k | 74,756 | BSD-3-Clause | — | 1,248 | 4,220 | 4,915 | 1,842 | 1,452 (`pkg.go.dev`) |
| rust-lang/rust | 122k | 64,731 | Apache-2.0 | — | 620 | 4,572 | 4,433 | 17,774 | 1,805 (`doc.rust-lang.org`) |
| dart-lang/sdk | 11k | 62,718 | BSD-3-Clause | `closed-duplicate`: 2,487 | 73 | 2,578 | 4,374 | 734 | 423 (`dart.dev`) |
| microsoft/terminal | 105k | 14,229 | MIT | `Resolution-Duplicate`: 3,881 | 86 | 3,856 | 4,336 | 2,562 | 90 (`learn.microsoft.com`) |
| python/cpython | 78k | 79,353 | NOASSERTION | — | 584 | 4,170 | 3,766 | 2,049 | 7,577 (`docs.python.org`) |
| home-assistant/core | 92k | 76,640 | Apache-2.0 | `duplicate`: 162 | 795 | 3,362 | 3,723 | 17,942 | 5,179 (`www.home-assistant.io`) |
| dotnet/runtime | 18k | 74,859 | MIT | — | 588 | 3,865 | 3,714 | 17,472 | 1,123 (`learn.microsoft.com`) |
| openai/codex | 136k | 41,610 | Apache-2.0 | — | 2,709 | 1,866 | 3,591 | 891 | 53 (`codex/blob/main/docs`) |
| oven-sh/bun | 97k | 19,381 | NOASSERTION | `duplicate`: 11 | 2,339 | 2,342 | 3,461 | 5,049 | 208 (`bun.sh/docs`) |
| zed-industries/zed | 95k | 23,786 | NOASSERTION | — | 1,714 | 2,311 | 3,314 | 5,832 | 601 (`zed.dev/docs`) |
| dotnet/roslyn | 21k | 37,009 | MIT | `Resolution-Duplicate`: 1,537 | 317 | 1,927 | 2,754 | 6,698 | 82 (`learn.microsoft.com`) |
| angular/angular | 101k | 31,168 | MIT | — | 330 | 2,493 | 2,613 | 5,144 | 486 (`angular.dev`) |
| spring-projects/spring-boot | 82k | 44,020 | Apache-2.0 | `status: duplicate`: 2,013 | 182 | 1,079 | 2,278 | 742 | 400 (`docs.spring.io/spring-boot`) |
| mui/material-ui | 99k | 20,631 | MIT | `duplicate`: 1,995 | 28 | 1,533 | 2,263 | 3,762 | 1,218 (`mui.com`) |
| dotnet/aspnetcore | 39k | 40,435 | MIT | `:heavy_check_mark: Resolution: Duplicate`: 1,468 | 279 | 996 | 2,147 | 3,725 | 852 (`learn.microsoft.com`) |
| grafana/grafana | 78k | 46,006 | AGPL-3.0 | `type/duplicate`: 950 | 109 | 1,715 | 2,125 | 12,557 | 1,209 (`grafana.com/docs`) |
| nextcloud/server | 38k | 21,901 | AGPL-3.0 | — | 274 | 1,893 | 1,976 | 3,558 | 1,036 (`docs.nextcloud.com`) |
| pandas-dev/pandas | 51k | 28,704 | BSD-3-Clause | `Duplicate Report`: 1,134 | 41 | 1,355 | 1,725 | 12,181 | 1,801 (`pandas.pydata.org`) |
| microsoft/WSL | 34k | 12,780 | MIT | `duplicate`: 1,443 | 22 | 1,040 | 1,683 | 95 | 282 (`learn.microsoft.com`) |
| immich-app/immich | 120k | 9,797 | AGPL-3.0 | — | 1,345 | 899 | 1,606 | 2,068 | 190 (`immich.app/docs`) |
| NixOS/nixpkgs | 27k | 60,369 | MIT | — | 340 | 1,457 | 1,531 | 17,286 | 445 (`nixos.org/manual`) |
| elastic/elasticsearch | 79k | 49,078 | NOASSERTION | — | 154 | 1,454 | 1,371 | 15,701 | 1,223 (`www.elastic.co/guide`) |
| pytorch/pytorch | 106k | 62,846 | NOASSERTION | — | 381 | 1,373 | 1,321 | 10,880 | 1,138 (`pytorch.org/docs`) |
| vercel/next.js | 144k | 25,799 | MIT | — | 312 | 1,164 | 1,285 | 4,810 | 1,752 (`nextjs.org/docs`) |
| kubernetes/kubernetes | 129k | 50,063 | Apache-2.0 | `triage/duplicate`: 52 | 16 | 1,362 | 1,214 | 11,894 | 2,337 (`kubernetes.io/docs`) |
| ansible/ansible | 72k | 33,542 | GPL-3.0 | — | 18 | 1,337 | 1,206 | 7,664 | 3,869 (`docs.ansible.com`) |
| moby/moby | 72k | 23,726 | Apache-2.0 | `kind/duplicate`: 57 | 56 | 1,227 | 1,167 | 3,474 | 1,950 (`docs.docker.com`) |
| python/mypy | 21k | 12,269 | NOASSERTION | — | 124 | 1,130 | 1,143 | 2,501 | 526 (`mypy.readthedocs.io`) |
| JuliaLang/julia | 49k | 26,620 | MIT | `duplicate`: 112 | 205 | 1,049 | 1,136 | 4,760 | 899 (`docs.julialang.org`) |
| neovim/neovim | 104k | 14,862 | NOASSERTION | `duplicate`: 556 | 190 | 897 | 1,103 | 3,702 | 95 (`neovim.io/doc`) |
| ziglang/zig | 43k | 13,514 | MIT | — | 173 | 1,052 | 1,094 | 3,115 | 141 (`ziglang.org/documentation`) |
| mastodon/mastodon | 51k | 13,362 | AGPL-3.0 | `duplicate`: 81 | 92 | 1,073 | 1,078 | 1,751 | 140 (`docs.joinmastodon.org`) |
| nodejs/node | 124k | 21,231 | NOASSERTION | `duplicate`: 559 | 74 | 962 | 1,073 | 5,046 | 841 (`nodejs.org/api`) |
| PowerShell/PowerShell | 56k | 13,693 | MIT | `Resolution-Duplicate`: 769 | 57 | 583 | 984 | 1,439 | 191 (`learn.microsoft.com`) |
| hashicorp/terraform | 50k | 21,845 | NOASSERTION | `duplicate`: 317 | 75 | 924 | 939 | 3,034 | 87 (`developer.hashicorp.com/terraform`) |
| tensorflow/tensorflow | 202k | 41,985 | Apache-2.0 | — | 142 | 970 | 925 | 3,718 | 3,710 (`www.tensorflow.org`) |
| electron/electron | 124k | 22,072 | MIT | `duplicate`: 29 | 77 | 901 | 924 | 2,485 | 372 (`www.electronjs.org/docs`) |
| pypa/pip | 10k | 7,829 | MIT | `resolution: duplicate`: 375 | 26 | 682 | 873 | 1,071 | 345 (`pip.pypa.io`) |
| denoland/deno | 109k | 15,247 | MIT | `duplicate`: 230 | 92 | 782 | 862 | 5,751 | 179 (`docs.deno.com`) |
| keycloak/keycloak | 38k | 21,417 | Apache-2.0 | — | 295 | 692 | 850 | 10,731 | 338 (`www.keycloak.org/docs`) |
| ollama/ollama | 188k | 11,639 | MIT | — | 713 | 130 | 799 | 893 | 598 (`ollama/blob/main/docs`) |
| rust-lang/rust-analyzer | 17k | 9,862 | Apache-2.0 | — | 138 | 707 | 785 | 3,125 | 137 (`rust-analyzer.github.io`) |
| alacritty/alacritty | 66k | 6,378 | Apache-2.0 | `F - duplicate`: 610 | 3 | 536 | 771 | 785 | 36 (`alacritty.org`) |
| vitejs/vite | 84k | 8,951 | MIT | `duplicate`: 339 | 133 | 605 | 732 | 2,200 | 91 (`vite.dev`) |
| jellyfin/jellyfin | 60k | 9,175 | GPL-2.0 | `duplicate`: 127 | 259 | 573 | 730 | 1,317 | 302 (`jellyfin.org/docs`) |
| hashicorp/terraform-provider-aws | 11k | 23,732 | MPL-2.0 | — | 146 | 745 | 729 | 9,644 | 463 (`registry.terraform.io/providers/hashicorp/aws`) |
| prettier/prettier | 52k | 7,409 | MIT | `type:duplicate`: 522 | 20 | 541 | 710 | 1,458 | 403 (`prettier.io/docs`) |
| matplotlib/matplotlib | 23k | 11,465 | none | `status: duplicate`: 447 | 66 | 527 | 707 | 2,810 | 1,325 (`matplotlib.org`) |
| rust-lang/cargo | 16k | 8,384 | Apache-2.0 | — | 190 | 665 | 681 | 1,952 | 289 (`doc.rust-lang.org/cargo`) |
| astral-sh/uv | 92k | 9,472 | Apache-2.0 | `duplicate`: 237 | 281 | 388 | 640 | 2,781 | 614 (`docs.astral.sh/uv`) |
| sveltejs/svelte | 90k | 9,316 | MIT | — | 72 | 622 | 611 | 2,755 | 250 (`svelte.dev/docs`) |
| numpy/numpy | 33k | 14,197 | NOASSERTION | `50 - Duplicate`: 137 | 34 | 613 | 609 | 2,619 | 179 (`numpy.org/doc`) |
| desktop/desktop | 22k | 13,826 | MIT | — | 205 | 530 | 594 | 954 | 24 (`docs.github.com/en/desktop`) |
| microsoft/winget-cli | 27k | 3,508 | MIT | `Resolution-Duplicate`: 444 | 8 | 640 | 559 | 375 | 45 (`learn.microsoft.com`) |
| nuxt/nuxt | 61k | 17,646 | MIT | — | 308 | 314 | 544 | 2,947 | 545 (`nuxt.com/docs`) |
| cli/cli | 47k | 6,746 | MIT | `duplicate`: 16 | 89 | 525 | 512 | 1,449 | 66 (`cli.github.com/manual`) |
| eslint/eslint | 28k | 11,104 | MIT | — | 31 | 519 | 477 | 1,968 | 706 (`eslint.org/docs`) |
| storybookjs/storybook | 92k | 14,858 | MIT | `duplicate`: 254 | 43 | 281 | 472 | 2,009 | 648 (`storybook.js.org/docs`) |
| obsproject/obs-studio | 80k | 5,358 | GPL-2.0 | — | 72 | 459 | 465 | 659 | 20 (`obsproject.com/kb`) |
| vuejs/core | 55k | 6,202 | MIT | `duplicate`: 10 | 70 | 441 | 462 | 1,612 | 354 (`vuejs.org`) |
| docker/compose | 39k | 8,464 | Apache-2.0 | `duplicate`: 133 | 23 | 402 | 459 | 1,230 | 599 (`docs.docker.com/compose`) |
| astral-sh/ruff | 51k | 8,476 | MIT | `duplicate`: 5 | 252 | 263 | 419 | 3,662 | 209 (`docs.astral.sh/ruff`) |
| scikit-learn/scikit-learn | 68k | 12,399 | BSD-3-Clause | — | 17 | 445 | 379 | 3,642 | 958 (`scikit-learn.org`) |
| tauri-apps/tauri | 113k | 6,611 | Apache-2.0 | — | 112 | 286 | 360 | 813 | 317 (`tauri.app`) |
| microsoft/playwright | 101k | 18,585 | Apache-2.0 | — | 128 | 264 | 348 | 3,734 | 1,907 (`playwright.dev/docs`) |
| rails/rails | 59k | 18,767 | MIT | `duplicate`: 1 | 11 | 424 | 348 | 2,967 | 540 (`guides.rubyonrails.org`) |
| bevyengine/bevy | 50k | 8,931 | Apache-2.0 | `S-Duplicate`: 78 | 79 | 328 | 341 | 3,230 | 75 (`docs.rs/bevy`) |
| expo/expo | 54k | 20,204 | MIT | `duplicate`: 16 | 30 | 361 | 332 | 3,029 | 933 (`docs.expo.dev`) |
| gohugoio/hugo | 91k | 8,322 | Apache-2.0 | `Duplicate`: 143 | 1 | 203 | 238 | 2,084 | 484 (`gohugo.io`) |
| huggingface/transformers | 169k | 19,923 | Apache-2.0 | `duplicate`: 1 | 17 | 243 | 214 | 4,343 | 489 (`huggingface.co/docs/transformers`) |
| ohmyzsh/ohmyzsh | 191k | 5,107 | MIT | `Resolution: duplicate`: 54 | 4 | 142 | 150 | 798 | 61 (`ohmyzsh/wiki`) |
| prometheus/prometheus | 68k | 6,655 | Apache-2.0 | `duplicate`: 7 | 24 | 173 | 137 | 1,139 | 367 (`prometheus.io/docs`) |
| microsoft/pyright | 16k | 7,658 | NOASSERTION | — | 11 | 149 | 134 | 103 | 32 (`pyright/blob/main/docs`) |
| webpack/webpack | 66k | 10,307 | MIT | — | 1 | 190 | 126 | 1,072 | 711 (`webpack.js.org`) |
| Homebrew/brew | 50k | 5,430 | BSD-2-Clause | — | 19 | 120 | 111 | 1,263 | 254 (`docs.brew.sh`) |
| langchain-ai/langchain | 150k | 10,666 | MIT | — | 38 | 107 | 94 | 1,388 | 419 (`python.langchain.com`) |
| facebook/react | 253k | 14,852 | MIT | `Resolution: Duplicate`: 311 | n/a | n/a | n/a | n/a | n/a |
| facebook/react-native | 127k | 28,095 | MIT | `Resolution: Duplicate`: 167 | n/a | n/a | n/a | n/a | n/a |

The 57 candidates that were not sampled have frames of 1,606 issues or fewer (immich-app/immich, NixOS/nixpkgs, elastic/elasticsearch next), except the two facebook/* repositories, which search refused (Caveats). With the usable shares seen in the sample (15% to 84% of the frame, median 44%), several of them could also reach 300, as microsoft/WSL's frame of 1,683 did, but their usable counts were not measured.

## The other counts the ticket asks for

- **Closing comments that link to the documentation.** Only a proxy could be counted at scale: closed issues whose comments contain one docs URL prefix per repository (GitHub's search matches the host as written, so `typescriptlang.org` finds 32 issues where `www.typescriptlang.org` finds 2,577). In the 12 sampled candidates, 0 to 35% of those hits had a maintainer's comment with the link in the 24 hours before the close (n = 12 to 20 per repository, [`05_docs_sample.json`](scripts/out/05_docs_sample.json)), which puts maintainer closing comments linking the docs between none and about 500 per repository (point estimates): well below the duplicates. The proxy misses other docs hosts and links written without the prefix, and the maintainer test relies on `authorAssociation`, which undercounts in organizations with private membership (below).
- **Issues closed by a pull request.** The `linked:pr` count covers closing references from pull requests. It undercounts where fixes do not arrive as GitHub pull requests: golang/go shows 1,842 of 65,546 closed issues, while 26,305 closed issues carry a "mentions this issue" comment (in the sample, `gopherbot`'s notice "Change https://golang.org/cl/N mentions this issue", which points to a code review change outside GitHub).
- **Total issues, docs location, license and how widely known**: in the tables. Every sampled candidate has more than 12,000 issues and between 11k and 196k stars. anthropics/claude-code has no license GitHub can detect: its `LICENSE.md` reads "© Anthropic PBC. All rights reserved. Use is subject to Anthropic's Commercial Terms of Service", and the repository holds issues, plugins and examples, not the product's source.

## Duplicate-detection bots seen in the sample

Comments by automation accounts that suggest or announce duplicates, found with [`bots.py`](scripts/bots.py) (issues with such a comment / sampled issues; "since" is the earliest one in the sample, not the bot's start):

| Repository | Account | Issues | Since | What it does |
|---|---|---:|---|---|
| anthropics/claude-code | `github-actions` | 16/40 | 2025-10 | "Found 3 possible duplicate issues", then closes as duplicate itself three days later (anthropics/claude-code#9337) |
| oven-sh/bun | `github-actions` | 10/41 | 2025-11 | "Found 3 possible duplicate issues" |
| oven-sh/bun | `robobun` | 5/41 | 2026-08 | closes as duplicate with an explanation (user account) |
| openai/codex | `github-actions` | 23/40 | 2026-02 | "Potential duplicates detected. Please review them and close your issue if it is a duplicate" |
| zed-industries/zed | `zed-community-bot` | 12/44 | 2026-03 | "This issue appears to be a duplicate of: #N" (suggestion) |
| microsoft/vscode | `vscodebot` | 5/46 | 2018-03 | "(Experimental duplicate detection) ... check if it is already covered by an existing one" |
| microsoft/vscode | `vs-code-engineering` | 5/46 | 2025-09 | closes known-error reports as not planned with "This issue is a duplicate of ...", and in 2026 closes as duplicate on its own (microsoft/vscode#340862) |
| microsoft/vscode | `vscode-triage-bot`, `vscodenpa` | 3/46, 5/46 | 2020-04, 2022-07 | execute a maintainer's `/duplicate` command |
| microsoft/PowerToys | `similar-issues-ai`, `github-actions` | 2/46, 4/46 | 2024-10, 2025-11 | "We've found some similar issues", "The following issues might be duplicates" |
| microsoft/PowerToys, microsoft/terminal, microsoft/WSL | `microsoft-github-policy-service` | 17/46, 5/44, 3/45 | 2023 | executes `/dup` commands; in microsoft/WSL#10421 it also acted on a plain "looks like a duplicate of #N" comment and a maintainer reopened it "due to overzealous bot" |
| microsoft/terminal, microsoft/WSL | `github-actions` | 2/44, 2/45 | 2024 | "AI powered bot that finds similar issues", "View similar issues" |
| dotnet/runtime, dotnet/aspnetcore | `MihuBot` | 1/44, 2/42 | 2025–2026 | "Here are possible related and/or duplicate issues (I may be wrong)" |
| microsoft/TypeScript | `typescript-bot` | 10/48 | 2019-04 | closes issues a maintainer labelled `Duplicate` after inactivity (the label, a human's, is the marking) |
| grafana/grafana | `grafanabot` | — | — | applies `type/duplicate` and closes after a human applies `bot/duplicate` |
| kubernetes/kubernetes | `k8s-ci-robot` | 7/41 | 2019-03 | executes `/close` and `/triage duplicate` (Prow) |

## Caveats

- **The frame is a lower bound.** It only reaches duplicates with a duplicate label, the duplicate close reason, or the words "duplicate of" in a comment. Maintainers who close with "Same as #N", "Tracked in #N" or "Merging to #N" are missed (that last phrasing is in microsoft/vscode#284349, which the frame only reached through its close reason).
- **Estimates are coarse.** 40 to 48 issues per repository give intervals of about ±10 to ±15 points on the share; the table carries them. The draws take two consecutive issues each, which clusters the sample slightly. The two search engines disagree a little: `"duplicate of" in:comments` gives 5,484 for microsoft/TypeScript with `type: ISSUE` and 5,184 with `ISSUE_ADVANCED`, which builds the frame.
- **`authorAssociation` is a weak proxy for "maintainer".** `MEMBER` means a member of the owning organization, not of the repository's team, and members whose membership is private show up as `CONTRIBUTOR` (seen across microsoft/vscode's team). The *maintainer comment only* tier rests on it; marking events do not (labels need triage access, `marked_as_duplicate` needs write access).
- **Inferred originals were not verified one by one.** They matter most for microsoft/TypeScript (14 of 32 maintainer-marked sampled issues), spring-projects/spring-boot (17 of 44) and microsoft/WSL (13 of 36); the headline excludes them.
- **Imported histories.** llvm/llvm-project's Bugzilla duplicates (2,393 issues with the Bugzilla line in a comment) are partly inside the frame and counted as *imported*, attributed to the person who wrote them where the migration mapped the account. python/cpython's bugs.python.org duplicates are in a metadata block of each migrated issue's body (3,883 issues match `"resolution = duplicate" in:body`, with the original in a `superseder` field that points to bugs.python.org; python/cpython#75960 shows the block's format), outside the frame. golang/go has 1,290 issues with "Merged into issue" and 618 with "Status changed to Duplicate" in comments, phrasings of its earlier Google Code tracker, also outside the frame and not classified.
- **Bot suggestions can anchor the ground truth.** Where a bot lists candidate duplicates before a maintainer decides (table above), the maintainer's marking is still the ground truth the ticket asks for, but it may lean toward what that bot's search found. Restricting eval cases to the period before such a bot started removes the doubt; the "since" dates above are only the earliest seen in the sample.
- **Bot markings are growing.** The bot-only cases cluster in 2025–2026 (anthropics/claude-code, oven-sh/bun, microsoft/vscode's `vs-code-engineering`).
- **Not checked**: whether the original still exists, is locked or was transferred; originals in another repository and pull requests were excluded.
- **Search refused two candidates.** For facebook/react and facebook/react-native the search API answered HTTP 422 ("The listed users and repositories cannot be searched either because the resources do not exist or you do not have permission to view them") with this token, although GraphQL `repository` reads them; only their label counts are shown (311 and 167).
- **ziglang/zig** is still listed, but its homepage now points to a post about migrating from GitHub to Codeberg.
- **The numbers drift**: every count is from 2026-11-20 and moves daily.
- **A repository's license covers its code.** Whether issue text can be redistributed (for the demo mode) is a separate question, not researched here.

## Incidental finding

GitHub's GraphQL `SearchType` enum lists `ISSUE_SEMANTIC` ("Returns results matching issues using semantic search") and `ISSUE_HYBRID` ("Returns results matching issues using hybrid (lexical + semantic) search") next to `ISSUE` and `ISSUE_ADVANCED` (introspection, 2026-11-20). Not explored here: it could serve as a baseline for duplicate search, but it searches today's index, with no cutoff.

## Sources

- GitHub Docs (read from the `github/docs` repository's `content/` tree): [Marking issues or pull requests as a duplicate](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/marking-issues-or-pull-requests-as-a-duplicate); [Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types); [Managing labels](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels); [Closing an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/closing-an-issue); [Issue status webhooks and workflows](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/issue-status-webhooks-and-workflows); [Searching issues and pull requests](https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests); [Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue); [REST: Timeline events](https://docs.github.com/en/rest/issues/timeline).
- GitHub GraphQL API, by introspection on 2026-11-20: `IssueClosedStateReason`, `IssueStateReason`, `ClosedEvent` (`duplicateOf`, `stateReason`, `closer`), `MarkedAsDuplicateEvent` (`canonical`, `duplicate` and their descriptions), `Issue.duplicateOf`, `SearchType`.
- GitHub GraphQL and REST APIs, queried by the scripts in [`scripts/`](scripts/); outputs in [`scripts/out/`](scripts/out/).
- The GitHub API research of #4: [`github-api-history.md`](https://github.com/jmbaquerosanchez/issue-triage-assistant/blob/research/github-api-history/docs/research/github-api-history.md).
