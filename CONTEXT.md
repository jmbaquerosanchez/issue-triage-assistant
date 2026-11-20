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

### Triage

**Triage**:
The preparation of a proposal of what to do with a new issue, for a maintainer to decide on.

**Duplicate**:
An issue that a maintainer marked as a duplicate of an earlier one.

**Original**:
The earlier issue that a duplicate was marked as a duplicate of.

**Duplicate candidate**:
An issue the system proposes as the original of a new issue, whether right or wrong.
_Avoid_: match, hit

### Evaluation

**Eval case**:
A historical issue together with its ground truth.

**Ground truth**:
The known correct answer for an eval case, taken from what a maintainer actually did.
_Avoid_: label, gold label, expected label

**Cutoff**:
The moment an eval case's issue was opened. Only what existed before it is visible when that case is replayed.
_Avoid_: snapshot, as-of date, time slice
