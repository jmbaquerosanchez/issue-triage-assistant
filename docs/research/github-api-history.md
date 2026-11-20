# GitHub API for ingesting a repository's history under a cutoff

> **Snapshot, 2026-11-20.** This report records what its sources said on that date and is not updated. Later research supersedes it by linking back here.

Research for ticket #4 of the phase-1 map (#2). Question: what do GitHub's REST and GraphQL APIs offer for downloading a repository's history so that every eval case can be replayed under its cutoff?

- **Date:** 2026-11-20. Rate limits, schema fields and observed behaviour can change; the facts below were true on that date.
- **Method:** GitHub's REST and GraphQL documentation, the live GraphQL schema (introspection), and about 60 read-only calls against two public repositories: `golang/go` (74,756 issues, used only as an example of a repository with tens of thousands of issues, not as a choice of target) and `cli/cli` (6,746 issues). Statements marked **observed** come from those calls and are not documented; everything else cites its doc page.
- **Scope:** facts and trade-offs only. The data model is decided in #13.

## Summary

| Need | REST | GraphQL |
|---|---|---|
| Duplicate marker and its original | `marked_as_duplicate` event, **without** the original; `state_reason: duplicate`, **without** the original | `MarkedAsDuplicateEvent.canonical/duplicate` (observed inverted), `ClosedEvent.duplicateOf`, `Issue.duplicateOf` |
| Who made it | `actor.type` (`User`, `Bot`, `Organization`), `performed_via_github_app` | `actor { __typename }`: `User`, `Bot`, `Organization`, `Mannequin`, `EnterpriseUserAccount` |
| Closing PR | `connected` event (observed `subject`), `cross-referenced` with the PR as source, `closed.commit_id` for commits; no PR on `closed` | `ClosedEvent.closer` (PR, commit or project), `Issue.closedByPullRequestsReferences`, `CrossReferencedEvent.willCloseTarget` |
| Edit history of bodies and comments | none: only the current body, title and `updated_at` | `userContentEdits` on issues and comments; each revision's full text (observed) |
| Title, state and labels at a date | `renamed`, `closed`/`reopened`, `labeled`/`unlabeled` events | same events in `timelineItems` |
| Full download of a repo with ~75k issues | ≈76,000 requests, ≈15 h at 5,000/h, and still no edit history | ≈4,000 to 5,000 points (about 1 h of quota), ≈2 to 3 h of latency, with a completeness caveat (see § 5) |

The two findings that most affect the eval:

1. **A large GraphQL page silently returns fewer timeline items.** The same issue's `timelineItems.totalCount` gets smaller when the enclosing `issues(first: N)` page gets bigger, with no error. It happened on both repositories (§ 5.4).
2. **There are two duplicate mechanisms, and each leaves different signals.** The older one (a `Duplicate of #N` comment) gives a `marked_as_duplicate` event. In GraphQL its `canonical` and `duplicate` fields came back swapped relative to their descriptions in 3 of 3 cases, and the target was sometimes *newer* than the issue marked. The newer one ("Close as duplicate", since December 2024) gives `stateReason: DUPLICATE` plus `duplicateOf`, and no `marked_as_duplicate` event (§ 1).

## 1. Duplicate markers and who made them

### What exists

**Mechanism A: a `Duplicate of #N` comment.** "type "Duplicate of" followed by an issue or pull request number in the body of a new comment", and "the user who creates the duplicate reference comment must have write access to the repository" for the event to appear. Undoing it "will add a new timeline event, indicating that the issue or pull request was unmarked" ([Marking issues or pull requests as a duplicate](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/marking-issues-or-pull-requests-as-a-duplicate)).

- REST: `marked_as_duplicate` and `unmarked_as_duplicate` events, in both the issue events API and the timeline API, for issues and PRs ([Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types)). They carry only the common properties (`id`, `actor`, `created_at`, `performed_via_github_app`…), **not the original**. Observed on `golang/go#29775`: the event has keys `actor, commit_id, commit_url, created_at, event, id, node_id, performed_via_github_app, url`. The original is only in the `commented` event with body `Duplicate of #6917`, which has the same `created_at` to the second.
- GraphQL: `MarkedAsDuplicateEvent` and `UnmarkedAsDuplicateEvent`, each with `actor`, `createdAt`, `canonical` ("The authoritative issue or pull request which has been duplicated by another"), `duplicate` ("The issue or pull request which has been marked as a duplicate of another") and `isCrossRepository` ([GraphQL reference: Issues](https://docs.github.com/en/graphql/reference/issues#markedasduplicateevent)).
- **Observed, the direction is inverted.** On `golang/go#29775` (comment `Duplicate of #6917`), `#29764` (`Duplicate of #39776`) and `#30185` (`Duplicate of #34054`), the event in the marked issue's timeline returns `canonical` = the marked issue itself and `duplicate` = the target of the comment. That is the reverse of the field descriptions. Treat the direction as unverified until it is checked on the target repository; the comment text is an independent source for it.
- **Observed, the target can be newer.** `#39776` was opened in June 2020, after `#29764` (January 2019), and `#34054` in September 2019, after `#30185` (February 2019). Maintainers sometimes fold an older issue into a newer one. Under a cutoff at the marked issue's creation, such a target does not exist yet.
- Mechanism A does not set `duplicateOf` and does not set the `DUPLICATE` state reason: `#29775` has `duplicateOf: null` and `stateReason: NOT_PLANNED`, and the `closed` event came in the same second as the marking (observed).

**Mechanism B: "Close as duplicate".** Launched in the UI on 2024-12-12: "select `Close as duplicate` from the dropdown to search for and select the duplicate issue" ([changelog](https://github.blog/changelog/2024-12-12-github-issues-projects-close-issue-as-a-duplicate-rest-api-for-sub-issues-and-more/)). The REST API can do it since 2025-07-17 ([changelog](https://github.blog/changelog/2025-07-17-duplicate-issues-create-from-anywhere-and-more/)).

- REST: the issue's `state_reason` enum includes `duplicate`, and updating takes `duplicate_issue_id` ([Issues](https://docs.github.com/en/rest/issues/issues)). Neither the issue object nor the `closed` event names the original. Observed on `cli/cli#14939`: the issue has only `closed_at, closed_by, state, state_reason` among its state keys, and its `closed` event has `state_reason: "duplicate"` and no reference.
- GraphQL: `IssueStateReason.DUPLICATE`, `Issue.duplicateOf` ("A reference to the original issue that this issue has been marked as a duplicate of") and `ClosedEvent.duplicateOf` ([GraphQL reference: Issues](https://docs.github.com/en/graphql/reference/issues#closedevent)). The argument `stateReason(enableDuplicate:)` was announced for removal on 2025-10-01 because "The state reason for duplicate issue is now returned by default" (schema introspection), and that matches what was observed.
- Observed: 4 of 4 `DUPLICATE` closures in `cli/cli` and 5 of 6 in `golang/go` (the latest 100 closed issues of each) had `duplicateOf` set and pointing to an older issue, and none had a `MarkedAsDuplicateEvent`. One `DUPLICATE` closure had `duplicateOf: null`.

**Repository conventions.** A `duplicate` label, or closing as "not planned" with a free-text comment, leave no duplicate-specific API signal beyond the label events and the comment. Observed: `golang/go#1` has a `labeled duplicate` event from 2009, when the issues were imported from another tracker.

**Prevalence (observed).** In a random sample of 188 `golang/go` issues: 4 with `stateReason: DUPLICATE` and 3 `MarkedAsDuplicateEvent`. Among the latest 100 closed issues: 6 `DUPLICATE` in `golang/go`, 4 in `cli/cli`.

### Who made it: a user or a bot

- GraphQL `actor` is the `Actor` interface, implemented by `Bot`, `EnterpriseUserAccount`, `Mannequin`, `Organization` and `User` (schema introspection). REST `actor.type` was observed as `User`, `Bot` and `Organization`. REST events and comments also carry `performed_via_github_app` ([Timeline](https://docs.github.com/en/rest/issues/timeline)).
- A `Bot` type only identifies GitHub Apps. Observed: all 106 `closed` events in the latest 100 closed `golang/go` issues have a `User` actor, and 52 of them were made by the project's automation account, which is an ordinary user account. Telling those apart takes a per-repository list of logins.
- Newer events carry an `intent` object ("The intent behind the agent's action, including rationale and confidence") on `ClosedEvent` and `LabeledEvent` in GraphQL, and on several REST timeline events (schema introspection; [Timeline](https://docs.github.com/en/rest/issues/timeline)).

### For the cutoff

Both mechanisms have a timestamp (the event's `createdAt`/`created_at`), so whether a marking existed at a given moment can be decided. Mechanism B's signal (`duplicateOf`) is GraphQL-only. Mechanism A's original needs GraphQL (with the observed inversion) or parsing the comment. An `unmarked_as_duplicate` event or a later reopen can undo either one.

## 2. Linking an issue to the pull request that closed it

### What exists

- **How links arise.** Closing keywords (`close`, `fixes`, `resolves`… and `OWNER/REPO#N` across repositories) in a PR description link the PR, and "When you merge a linked pull request into the default branch of a repository, its linked issue is automatically closed". The keywords are "interpreted only when the pull request targets the repository's default branch". "Anyone with write permissions" can link manually from the sidebar, "up to ten issues to each pull request". Keywords in a commit message close the issue, "but the pull request that contains the commit will not be listed as a linked pull request" ([Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)).
- **GraphQL `ClosedEvent.closer`** is the union `Commit | ProjectV2 | PullRequest`, "Object which triggered the creation of this event" ([GraphQL reference: Issues](https://docs.github.com/en/graphql/reference/issues#closedevent); schema introspection). Observed on `cli/cli#15019`: `closer` = PR #15065 with its `mergeCommit`. On `golang/go`, which lands changes through commits, 50 of 106 close events had `closer: Commit` and 56 had none (closed by hand).
- **GraphQL `Issue.closedByPullRequestsReferences`**: "List of open pull requests referenced from this issue", with arguments `includeClosedPrs` (default `false`), `userLinkedOnly`, `excludeUserLinked` and `orderByState` (schema introspection). Observed: with `includeClosedPrs: true` it returns the merged PR #15065. It is a snapshot of the current links, with no date.
- **GraphQL `CrossReferencedEvent`**: `source`, `target`, `referencedAt`, `isCrossRepository`, `willCloseTarget` ("Checks if the target will be closed when the source is merged"). `ConnectedEvent`/`DisconnectedEvent` (manual links): `source`, `subject`, `isCrossRepository` ([GraphQL reference: Issues](https://docs.github.com/en/graphql/reference/issues#crossreferencedevent)). Observed: on `cli/cli#15019` the PR's cross-reference had `willCloseTarget: false` and the link came from a `ConnectedEvent`.
- **REST.** The `closed` event has `commit_id` when "the commit that closed it" used closing syntax ([Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types)). Observed: `commit_id` set on `golang/go#82840`, but `null` and no PR reference on `cli/cli#15019`, which a PR closed. The `cross-referenced` event (timeline API only) carries `source.issue`, which for a PR has a `pull_request` key with `merged_at`, and has no `willCloseTarget`. The `connected` event has an undocumented `subject` object with the PR's `type`, `number`, `state`, `merged_at` and `repository` (observed).

### For the cutoff

Each of the events above has a date, so a link can be placed in time. `closedByPullRequestsReferences` is undated and reflects today's links. The "closed by PR" fact in its cleanest form (`ClosedEvent.closer`) is GraphQL-only. From REST it has to be inferred from a `connected` or `cross-referenced` event plus the PR's `merged_at` and the close time.

## 3. Edit history of issue bodies and comments

### What exists

- **REST has no edit history.** The issues, comments, events and timeline references expose only the current `body`, `title` and `updated_at` ([Issues](https://docs.github.com/en/rest/issues/issues), [Comments](https://docs.github.com/en/rest/issues/comments), [Timeline](https://docs.github.com/en/rest/issues/timeline)). A `commented` timeline event's `body` is the current text, and its `updated_at` is "the time the comment was updated or created" ([Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types)).
- **GraphQL** `Issue` and `IssueComment` have `userContentEdits` (connection), `lastEditedAt`, `editor` and `includesCreatedEdit` ("Check if this comment was edited and includes an edit with the creation data") ([GraphQL reference: Issues](https://docs.github.com/en/graphql/reference/issues#issue)). `UserContentEdit` has `editedAt`, `createdAt`, `updatedAt`, `deletedAt`, `deletedBy`, `editor` and `diff`, described as "A summary of the changes for this edit" ([GraphQL reference: Users](https://docs.github.com/en/graphql/reference/users#usercontentedit); schema introspection).
- **Observed, `diff` is the full text of each revision, not a diff.** On `golang/go#82860` (5 revisions), the nodes come newest first. The newest node's `diff` equals the current `body` byte for byte. The oldest node has `editedAt` equal to the issue's `createdAt` (it is the original text: `includesCreatedEdit: true`), while its `createdAt` is the moment of the first edit. The text at a cutoff `t` is therefore the `diff` of the newest revision with `editedAt <= t`, and the current body if the item was never edited (`lastEditedAt: null`, empty history).
- **Titles** change through `renamed` events (REST `rename.from`/`rename.to`) or `RenamedTitleEvent` (`previousTitle`, `currentTitle`) ([Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types); [GraphQL reference: Issues](https://docs.github.com/en/graphql/reference/issues#renamedtitleevent)).
- **Retention.** "A 100-edit maximum applies to issues, issue comments, pull requests, pull request review comments, and commit comments". Beyond that "the oldest intermediate edits are automatically removed", while "the original content and the most recent 99 edits are always preserved" ([Tracking changes in a comment](https://docs.github.com/en/communities/moderating-comments-and-conversations/tracking-changes-in-a-comment)).
- **Deleted revisions.** Comment authors and users with write access can "Delete revision from history". The editor and the time stay visible, but the content does not (same page). In the schema this maps to `deletedAt` and `deletedBy`. A deleted revision was not observed, so it is unknown whether `diff` then comes back `null`.
- **Deleted comments** disappear. GraphQL keeps a `CommentDeletedEvent` (`createdAt`, `deletedCommentAuthor`) with no content (schema introspection). The REST timeline schema lists no such event ([Timeline](https://docs.github.com/en/rest/issues/timeline)).
- **Minimized comments**: `isMinimized` and `minimizedReason` describe the current state, with no date (schema introspection). REST `commented` events carry a `minimized` key (observed).
- **How often (observed, random sample of 188 `golang/go` issues).** 18% of issue bodies and 9.8% of the 984 comments seen had `lastEditedAt` set.

### For the cutoff

Reconstructing a body or comment as it was before an edit is possible only through GraphQL `userContentEdits`. It is exact except when the item exceeded 100 edits (intermediate revisions are lost) or a revision was deleted. A comment deleted after the cutoff is missing from the past view: information is lost, but nothing from the future leaks. Only items with `lastEditedAt` set need their history fetched.

## 4. Rebuilding an issue's state and labels at a given date

### What exists

- **Events:** `closed`, `reopened`, `labeled`, `unlabeled`, `renamed`, `milestoned`, `demilestoned`, `assigned`, `unassigned`, `locked`, `unlocked`, `transferred` and `converted_to_discussion`, all in both REST APIs; plus issue type, sub-issue, parent-issue and blocking events ([Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types); [Timeline](https://docs.github.com/en/rest/issues/timeline)). In GraphQL these are `timelineItems` types, which can be filtered with `itemTypes` and `since` (schema introspection).
- **Payloads.** REST `labeled`/`unlabeled` carry `label.name` and `label.color` ([Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types)). GraphQL `LabeledEvent.label` is a `Label` object. GraphQL `ClosedEvent.stateReason` and `ReopenedEvent.stateReason` give the reason. REST `closed` events carry a `state_reason` key that the event-types page does not list (observed: `not_planned` on `golang/go#29775`, `duplicate` on `cli/cli#14939`, `null` on `cli/cli#15019`, where GraphQL says `COMPLETED`).
- **Where to read them.**
  - Per issue: `GET /repos/{owner}/{repo}/issues/{n}/timeline` (everything, comments included) or `.../issues/{n}/events` (no comments, no cross-references), `per_page` up to 100 ([Timeline](https://docs.github.com/en/rest/issues/timeline), [Events](https://docs.github.com/en/rest/issues/events)). No retention limit was observed: `golang/go#29775` returns events from 2019, and `#2` from 2009.
  - Repository-wide: `GET /repos/{owner}/{repo}/issues/events` has no `since` parameter ([Events](https://docs.github.com/en/rest/issues/events)). **Observed:** page 301 at `per_page=100` returns `422` ("pagination is limited for this resource"), so the listing reaches only the latest 30,000 events. For `golang/go` that went back only to 2026-09-10, about ten weeks.
- **Rebuild rule the data allows.** Start from open, no labels, and the title before the first rename. Apply events in `created_at` order up to the cutoff.

### Gaps observed

- **Imported issues lack events.** `golang/go` issues 1 to 100 (imported in 2014) are closed with `closedAt` 2014-12-08 but have no `ClosedEvent`, and REST `closed_by` is `null`.
- **A deleted label leaves no `unlabeled`.** `golang/go#2` has `labeled fixed` (2009) and no `unlabeled`. The label returns `404` today, and the issue's current labels are only `FrozenDueToAge`. Replaying the events would keep `fixed` on forever.
- Replaying to "now" and comparing with the current `state`, `stateReason` and labels exposes both gaps. Nothing in the API records the date of an imported close or of a label deletion.

### For the cutoff

Title, state, state reason and labels at a date can all be rebuilt from events, in REST or in GraphQL. The gaps above make the replay incomplete for imported issues and deleted labels. The repository-wide events listing cannot serve a full history, so the events come per issue (REST) or inside the issue pages (GraphQL).

## 5. Rate limits, authentication and the cost of a full download

### 5.1 Authentication

- **Unauthenticated REST:** 60 requests per hour per IP ([REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)), too few for any download.
- **Any token reads public repositories.** "All fine-grained personal access tokens include read access to public repositories" ([Forming calls with GraphQL](https://docs.github.com/en/graphql/guides/forming-calls-with-graphql)), and a classic token "with no assigned scopes can only access public information" ([Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)). GraphQL is called with a personal access token, a GitHub App or an OAuth app ([Forming calls with GraphQL](https://docs.github.com/en/graphql/guides/forming-calls-with-graphql)).

### 5.2 Primary limits

| Credential | REST requests/h | GraphQL points/h |
|---|---|---|
| Personal access token (user) | 5,000 | 5,000 |
| GitHub App installation, not on Enterprise Cloud | 5,000, +50 per repo over 20 and per org user over 20, up to 12,500 | same rule, up to 12,500 |
| GitHub App installation on an Enterprise Cloud org | 15,000 | 10,000 |
| `GITHUB_TOKEN` in Actions | 1,000 per repository | 1,000 per repository |

Sources: [REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [GraphQL rate and query limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api). The REST and GraphQL budgets are separate (observed: `gh api rate_limit` reports `core` and `graphql` apart).

**GraphQL point cost.** Add up the requests each connection would need, "assuming every connection hits its `first` or `last` limit". Divide by 100 and round, with a minimum of 1. `first`/`last` go from 1 to 100, the cap is 500,000 nodes per call, and a query taking over 10 seconds is cut with a `502`/`504` and "deducts additional points" ([GraphQL rate and query limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api)). `rateLimit(dryRun: true)` computes a query's cost without running it (schema introspection).

### 5.3 Secondary limits and pacing

- No more than 100 concurrent requests across REST and GraphQL. Per endpoint, 900 points per minute for REST and 2,000 for GraphQL (1 point per GET or query). No more than 90 s of CPU time per 60 s of real time, at most 60 s of it for GraphQL ([REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)).
- On a limit, the response is a `403`/`429`. Wait for `retry-after`, or until `x-ratelimit-reset`, or at least a minute, then back off exponentially. "Continuing to make requests while you are rate limited may result in the banning of your integration". There is no way to check the secondary status in advance (same page). The best-practices page says to "make requests serially instead of concurrently", and that a conditional request answered `304` "does not count against your primary rate limit" ([Best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)).
- **Pagination.** REST `per_page` is at most 100, and the `last` link is omitted when it "can't be calculated" ([Pagination in the REST API](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)). Observed caps:
  - Repository-wide `issues/events` and `issues/comments` stop at 30,000 items (`last` = page 300 at `per_page=100` and page 600 at `per_page=50`, and page 301 returns `422`). The comments listing has a `since` (last-updated) filter and `sort=updated` ([Comments](https://docs.github.com/en/rest/issues/comments)), so it can be walked in windows. The events listing cannot.
  - `GET /repos/{owner}/{repo}/issues` at `page=400` returns `422`: "Pagination with the page parameter is not supported for large datasets, please use cursor based pagination (after/before)". The `Link` header already carries an `after` cursor.
  - This listing also returns PRs ("You can identify pull requests by the `pull_request` key", [Issues](https://docs.github.com/en/rest/issues/issues)). GraphQL `Repository.issues` returns only `Issue` nodes, and PRs come from `pullRequests` (schema introspection).

### 5.4 Observed: large GraphQL pages silently drop timeline items

Same query shape `issues(first: N, orderBy: CREATED_AT ASC) { timelineItems(first: 1) { totalCount } }`, compared over the oldest issues:

| Repository | Sum of `totalCount` over | N = 10 | N = 25 | N = 50 | N = 75 | N = 99 or 100 |
|---|---|---|---|---|---|---|
| `golang/go` | the oldest 25 issues | | 1,654 | 1,654 | 1,631 | 1,606 |
| `cli/cli` | the oldest 10 issues | 209 | 209 | 184 | | |
| `cli/cli` | the oldest 25 issues | | 391 | | | 309 |

- No errors were returned, `totalCount` itself shrinks, and `hasNextPage` does not reveal the gap. The result repeated on a second run.
- The dropped items included `ReferencedEvent`, `LabeledEvent`, `LockedEvent` and `UnassignedEvent`.
- The small-page counts match REST: `golang/go#10` has 11 items via the REST timeline and via GraphQL at N ≤ 50, but 7 at N = 99. `cli/cli#46` has 3 via REST and at N = 10, but 1 at N = 50.
- The safe page size differs by repository: 50 was fine for `golang/go` and not for `cli/cli`. The docs only say "Queries that exceed other resource limits return partial results along with an error" ([GraphQL rate and query limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api)), and here no error came back.

### 5.5 Worked estimate: a repository with ~75,000 issues

**Inputs, from `golang/go` on 2026-11-20:**

- 74,756 issues and 5,664 PRs (GraphQL `totalCount`).
- Random sample of 188 issues: mean 5.23 comments (median 3.5, p90 12) and mean 9.19 timeline items, comments included (median 6, p90 21, max 81, none over 100). Among the oldest 100 issues, one has 1,099 items.
- 18% of bodies and 9.8% of comments edited.
- Totals extrapolated from the sample: ≈391,000 comments, ≈687,000 timeline items, ≈13,500 edited bodies, ≈38,000 edited comments.

**Option R: REST only.**

| Step | Requests |
|---|---|
| `GET /issues?state=all&per_page=100`, cursor pagination (issues + PRs) | ≈805 |
| `GET /issues/{n}/timeline?per_page=100`, one per issue | 74,756 |
| Extra timeline pages for issues over 100 items (≤1% assumed) | ≈750 |
| **Total** | **≈76,300** |

- **Time:** ≈15.3 h at 5,000/h, ≈6.1 h at 12,500/h (App maximum), ≈76 h with `GITHUB_TOKEN` (1,000/h).
- The 900-points-per-minute secondary limit (54,000/h) does not bind.
- Measured latency was 1.5 to 2.0 s per call through the `gh` CLI, process start included. The hourly quota allows one request every 0.72 s, so a serial client with sub-second latency is quota-bound.
- **It cannot rebuild edited bodies or comments** (§ 3).
- Using the repository-wide comments listing instead of timeline comments does not save requests, because events older than the latest 30,000 still need one call per issue.

**Option G: GraphQL only.** Bulk query: a page of N issues with title, body, state, `duplicateOf`, `labels(first: 20)`, `userContentEdits(first: 20)` with the revision texts, and `timelineItems(first: 100)` with the item types of §§ 1 to 4 and comment bodies.

| Step | Queries | Points |
|---|---|---|
| Bulk pages at N = 50 (dry-run cost 2 per page) | 1,496 | 2,992 |
| or bulk pages at N = 25 (dry-run cost 1 per page) | 2,991 | 2,991 |
| Extra timeline pages for issues over 100 items (≤1% assumed, 1 point each) | ≈750–1,500 | ≈750–1,500 |
| Comment edit histories: `nodes(ids: [100 comment ids]) { userContentEdits(first: 20) }` (measured: 1 point, 2.6 s) | ≈383 | ≈383 |
| **Total** | **≈2,600–4,900** | **≈4,100–4,900** |

- **Points:** about one hour of a 5,000-point budget.
- **Wall time:** measured on the 50 and 100 oldest (heaviest) `golang/go` issues, a page took 4.4 s at N = 50 (385 KB) and 7.0 s at N = 100 (636 KB), the latter close to the 10 s timeout. Serially that is ≈2 to 3 h in all.
- **Parallelism:** the GraphQL CPU limit (60 s per minute) caps it. Server CPU time is not exposed, so how much parallelism helps is unknown.
- **Completeness:** § 5.4 applies. Points do not shrink with smaller pages, since the cost is about 1 point per 25 issues either way, but no page size is documented as complete.
- Nesting edit histories inside timeline comments would multiply the cost: 100 issues × 100 items gives 10,000 requests, about 100 points per page. That is why the comment histories are fetched by ID in a separate step.

**Option H: REST timelines plus GraphQL for edit histories only.** ≈76,300 REST requests (≈15 h at 5,000/h). On top of that, about 135 GraphQL points for edited issue bodies (`nodes(ids:)` in batches of 100) and ≈383 for edited comments. The REST and GraphQL budgets are separate, so the GraphQL part runs alongside. This gets the REST timeline's consistency (§ 5.4) at REST's time cost.

### 5.6 Incremental updates

Out of scope for this ticket (the map lists it under "Not yet specified"). The hooks exist: REST `since` on issues and comments (last-updated), GraphQL `issues(filterBy: {since})` and `timelineItems(since:)`, and `304` conditional requests that cost nothing ([Issues](https://docs.github.com/en/rest/issues/issues), [Comments](https://docs.github.com/en/rest/issues/comments), [Best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api); schema introspection).

## 6. Other facts that touch the cutoff

- **Numbering gaps.** Issues, PRs and other items share one number space. On `golang/go` the highest number was 83,211, against 80,420 issues and PRs; the gap was not broken down.
- **Transferred or deleted issues.** Fetching one returns `301` (transferred), `404` (transferred to or deleted from a repository you cannot read) or `410` (deleted) ([Issues](https://docs.github.com/en/rest/issues/issues)). Issues transferred in carry a `transferred` event / `TransferredEvent.fromRepository`. An original that was later deleted or transferred out cannot be fetched from the target repository.
- **Cross-repository duplicates** carry `isCrossRepository: true`, and their original lives in another repository.
- **Current-only fields.** `Issue.body`, `title`, `labels`, `state`, `isMinimized`, `reactionGroups` and `closedByPullRequestsReferences` describe today. Only events and `userContentEdits` carry history.
- **API versions.** The REST docs now show `X-GitHub-Api-Version: 2026-03-10` ([Timeline](https://docs.github.com/en/rest/issues/timeline)). `gh` was served `2022-11-28` (observed header `X-Github-Api-Version-Selected`). Response shapes were not compared across versions.

## Open caveats

1. **The GraphQL timeline truncation (§ 5.4) is undocumented.** Neither its cause nor a guaranteed-safe page size is known. It was seen on two repositories, in sums over small samples.
2. **The `canonical`/`duplicate` inversion was seen in 3 of 3 cases in one repository.** It was not checked on others, or on PRs.
3. **The sample statistics come from one repository.** 188 random issues and 984 comments set the per-issue means; other repositories will differ, and the estimate scales with them.
4. **Not observed:** a deleted revision's `diff`; whether `LabeledEvent.label` shows a renamed label's old or new name; how deleted accounts appear as actors in events. The pages read do not specify them.
5. **Imported issues and deleted labels break event replay.** The extent depends on the target repository's own history.

## Sources

REST:

- [Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types)
- [Timeline events](https://docs.github.com/en/rest/issues/timeline)
- [Issue events](https://docs.github.com/en/rest/issues/events)
- [Issues](https://docs.github.com/en/rest/issues/issues)
- [Issue comments](https://docs.github.com/en/rest/issues/comments)
- [Pagination in the REST API](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
- [Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Best practices for using the REST API](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)

GraphQL:

- [Reference: Issues](https://docs.github.com/en/graphql/reference/issues)
- [Reference: Users](https://docs.github.com/en/graphql/reference/users)
- [Rate limits and query limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api)
- [Using pagination in the GraphQL API](https://docs.github.com/en/graphql/guides/using-pagination-in-the-graphql-api)
- [Forming calls with GraphQL](https://docs.github.com/en/graphql/guides/forming-calls-with-graphql)
- Live schema introspection of `MarkedAsDuplicateEvent`, `UnmarkedAsDuplicateEvent`, `ClosedEvent`, `Closer`, `IssueStateReason`, `IssueTimelineItemsItemType`, `Issue`, `IssueComment`, `UserContentEdit`, `Actor` and `Query.rateLimit`, on 2026-11-20

Product docs and changelog:

- [Marking issues or pull requests as a duplicate](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/marking-issues-or-pull-requests-as-a-duplicate)
- [Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
- [Tracking changes in a comment](https://docs.github.com/en/communities/moderating-comments-and-conversations/tracking-changes-in-a-comment)
- [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Changelog 2024-12-12: close issue as a duplicate](https://github.blog/changelog/2024-12-12-github-issues-projects-close-issue-as-a-duplicate-rest-api-for-sub-issues-and-more/)
- [Changelog 2025-07-17: duplicate issues via the REST API](https://github.blog/changelog/2025-07-17-duplicate-issues-create-from-anywhere-and-more/)
