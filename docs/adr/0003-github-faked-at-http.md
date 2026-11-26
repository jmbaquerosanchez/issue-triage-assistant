# GitHub faked at HTTP, and every test history built by the real ingestion

Tests never talk to GitHub and never write the history directly. A local fake HTTP server serves a synthetic repository as it stood at an instant the test sets, the `github` client points at it through its base URL, and every test that needs a history builds it by ingesting a scenario (a typed list of dated changes, each with the account that made it) through the real ingestion. So a test of duplicate search or of the eval runs an HTTP server and the whole ingestion in its setup. We accept that because what crosses the seam is exactly what each ingestion archives as raw responses, so pagination, parsing and the merge into the history run in every test; because the same fake serves the in-process tests and the subprocess ones (the MCP server, the `demo` flow); and because the history keeps one write path, so no test can build a history that ingestion would never write.

## Considered Options

- **A typed port (`fetchIssuesSince`, `fetchIssue`, `countIssues`…) with an in-memory fake**: rejected. Pagination and parsing would never run in CI, and subprocess tests would need another mechanism.
- **A builder that writes the history directly**: setup would be faster and failures more local. Rejected because it opens a second write path that drifts from ingestion's.

## Consequences

- The fake answers the client's few queries by operation name. It is not a GraphQL engine, so it does not check the query text: real ingestions do, and the parsing also runs in CI against responses recorded from this repository's own tracker, which is public and holds only its own text.
- A bug in ingestion fails the tests of every module built on the history, not only ingestion's.
- `ISSUE_TRIAGE_ASSISTANT_GITHUB_URL` points the packed package at the fake in subprocess tests. `GITHUB_TOKEN` is sent only to github.com, never to an overridden base URL, so the fake never sees it.
- The snapshot date is the `Date` header of an ingestion's first response, so tests set the fake's instant instead of injecting a clock.
