# Issue triage

Helping the maintainers of an open source repository triage new issues, and measuring how well that is done by replaying the repository's own history.

## Language

### Repositories and their issues

**Target repository**:
The GitHub repository whose issues are ingested and triaged.
_Avoid_: upstream, source project, project

**Issue**:
An issue of the target repository. The work items of this codebase are tickets, never issues.
_Avoid_: ticket

**Maintainer**:
A person with permissions on the target repository who decides what to do with an issue.

**Label**:
A GitHub label on an issue, such as `duplicate` or `bug`.
_Avoid_: tag; using it for ground truth

**Snapshot**:
The history of a target repository as ingested up to a moment. An eval runs on one and declares its date; the demo ships the index of one. Not a cutoff: a cutoff belongs to each eval case, a snapshot to each ingestion.
_Avoid_: dump, export

### Triage

**Triage**:
The preparation of a proposal of what to do with a new issue, for a maintainer to decide on.

**New issue**:
The issue being triaged, whose duplicates are searched: one just opened, one about to be opened, or, in a replay, the eval case's issue as of its cutoff.
_Avoid_: query, incoming issue

**Duplicate**:
An issue that a maintainer marked as a duplicate of another.

**Original**:
The issue a duplicate was marked as a duplicate of: usually earlier, sometimes newer, when a maintainer folds an old issue into a newer one.

**Duplicate cluster**:
The issues joined by maintainers' duplicate markings, directly or through a chain: a duplicate, its original, that original's own original, and the other duplicates of any of them.
_Avoid_: duplicate group, family

**Duplicate candidate**:
An issue the system proposes as the original of a new issue, whether right or wrong.
_Avoid_: match, hit

**Piece**:
The text of an issue (its title and body) or of a comment, as it stood between two edits: the unit that duplicate search scores.
_Avoid_: chunk, document, passage, entry

### Evaluation

**Eval case**:
A historical issue together with its ground truth.

**Ground truth**:
The known correct answer for an eval case, taken from what a maintainer actually did.
_Avoid_: label, gold label, expected label

**Cutoff**:
The moment an eval case's issue was opened. Only what existed before it is visible when that case is replayed.
_Avoid_: as-of date, time slice

**Replay**:
Running an eval case as of its cutoff: the search sees everything that existed before the cutoff, back to the start of the target repository's history, and nothing after.
_Avoid_: simulation, backtest

**Lenient replay**:
A replay that mimics triage-bench's protocol and lets through, on purpose, the leaks a replay excludes, to measure how much each one moves the numbers. _Replay_ alone always means the strict one.
_Avoid_: loose replay, baseline replay

**Correction**:
One step from the lenient replay toward the replay that removes one leak or bias, so its effect on the numbers can be measured.
_Avoid_: fix, adjustment

**Leak**:
Anything from after an eval case's cutoff that reaches its replay: text edited later, comments or labels added later, scoring statistics that count later issues.
_Avoid_: lookahead
