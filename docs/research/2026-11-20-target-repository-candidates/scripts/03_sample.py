"""Step 3: sample issues from each shortlisted repo's duplicate frame and fetch their timelines.

Frame: the `union` query of step 2 (duplicate label OR reason:duplicate OR "duplicate of" in comments).
Sampling: stratified by creation year, proportional allocation of N_SAMPLE issues; inside a year,
random start dates, taking the next 2 issues by creation date from each (search `sort:created-asc`).
Seeded, so a rerun draws the same windows (search results may still drift as GitHub's index changes).

Output: out/03_samples/<owner>__<name>.json (raw; includes comment bodies, so it is NOT committed).
"""
import datetime as dt
import json
import pathlib
import random
import sys
import time

from gh_graphql import graphql

HERE = pathlib.Path(__file__).parent
meta = json.loads((HERE / "out" / "01_repo_metadata.json").read_text())
counts = json.loads((HERE / "out" / "02_counts.json").read_text())
OUT = HERE / "out" / "03_samples"
OUT.mkdir(exist_ok=True)

N_SAMPLE = 40
PER_WINDOW = 2
TODAY = dt.date(2026, 11, 20)

SHORTLIST = [l.strip() for l in (HERE / "shortlist.txt").read_text().splitlines() if l.strip()]
if len(sys.argv) > 1:
    SHORTLIST = sys.argv[1:]

ISSUE_FIELDS = """
... on Issue {
  number createdAt closedAt state stateReason
  author { login __typename }
  duplicateOf { number createdAt repository { nameWithOwner } }
  timelineItems(first: 100, itemTypes: [LABELED_EVENT, UNLABELED_EVENT, MARKED_AS_DUPLICATE_EVENT,
                UNMARKED_AS_DUPLICATE_EVENT, CLOSED_EVENT, REOPENED_EVENT, ISSUE_COMMENT]) {
    totalCount
    nodes {
      __typename
      ... on LabeledEvent { createdAt actor { login __typename } label { name } }
      ... on UnlabeledEvent { createdAt actor { login __typename } label { name } }
      ... on MarkedAsDuplicateEvent {
        createdAt isCrossRepository actor { login __typename }
        canonical {
          __typename
          ... on Issue { number createdAt repository { nameWithOwner } }
          ... on PullRequest { number createdAt repository { nameWithOwner } }
        }
        duplicate {
          __typename
          ... on Issue { number createdAt repository { nameWithOwner } }
          ... on PullRequest { number createdAt repository { nameWithOwner } }
        }
      }
      ... on UnmarkedAsDuplicateEvent {
        createdAt actor { login __typename }
        canonical { __typename ... on Issue { number } ... on PullRequest { number } }
      }
      ... on ClosedEvent {
        createdAt stateReason actor { login __typename } closer { __typename }
        duplicateOf {
          __typename
          ... on Issue { number createdAt repository { nameWithOwner } }
          ... on PullRequest { number createdAt repository { nameWithOwner } }
        }
      }
      ... on ReopenedEvent { createdAt actor { login __typename } }
      ... on IssueComment { createdAt authorAssociation author { login __typename } body }
    }
  }
}
"""


def frame_terms(repo: str) -> str:
    labels = counts[repo]["dup_labels"]
    terms = [f'label:"{l}"' for l in labels] + ["reason:duplicate", '"duplicate of" in:comments']
    return f"repo:{repo} is:issue ({' OR '.join(terms)})"


def year_counts(repo: str) -> dict:
    first = int(meta[repo]["createdAt"][:4])
    years = list(range(first, TODAY.year + 1))
    parts = [
        f"y{y}: search(type: ISSUE_ADVANCED, query: {json.dumps(frame_terms(repo) + f' created:{y}-01-01..{y}-12-31')}) {{ issueCount }}"
        for y in years
    ]
    data = graphql("{ " + "\n".join(parts) + " }")["data"]
    return {y: data[f"y{y}"]["issueCount"] for y in years}


def allocate(yc: dict, n: int) -> dict:
    total = sum(yc.values())
    raw = {y: n * c / total for y, c in yc.items()}
    alloc = {y: int(v) for y, v in raw.items()}
    for y in sorted(raw, key=lambda y: raw[y] - alloc[y], reverse=True)[: n - sum(alloc.values())]:
        alloc[y] += 1
    return {y: k for y, k in alloc.items() if k}


def sample_repo(repo: str) -> None:
    out_file = OUT / (repo.replace("/", "__") + ".json")
    if out_file.exists():
        print("skip", repo)
        return
    rng = random.Random(repo)
    yc = year_counts(repo)
    alloc = allocate(yc, N_SAMPLE)
    windows = []
    for y, k in alloc.items():
        start, end = dt.date(y, 1, 1), min(dt.date(y, 12, 31), TODAY)
        span = (end - start).days
        for _ in range((k + PER_WINDOW - 1) // PER_WINDOW):
            d = start + dt.timedelta(days=rng.randrange(max(span, 1)))
            windows.append((y, d.isoformat(), end.isoformat()))
    issues = {}
    for i in range(0, len(windows), 5):
        chunk = windows[i : i + 5]
        parts = []
        for j, (y, d, end) in enumerate(chunk):
            query = frame_terms(repo) + f" created:{d}..{end} sort:created-asc"
            parts.append(
                f"w{j}: search(type: ISSUE_ADVANCED, first: {PER_WINDOW}, query: {json.dumps(query)}) {{ nodes {{ {ISSUE_FIELDS} }} }}"
            )
        data = graphql("{ " + "\n".join(parts) + " rateLimit { cost remaining } }")["data"]
        for j, (y, d, end) in enumerate(chunk):
            for node in data[f"w{j}"]["nodes"]:
                node["_stratum"] = y
                node["_window_start"] = d
                issues.setdefault(node["number"], node)
        print(repo, i, data["rateLimit"])
        time.sleep(1)
    out_file.write_text(json.dumps({"repo": repo, "year_counts": yc, "alloc": alloc, "issues": list(issues.values())}))


for repo in SHORTLIST:
    sample_repo(repo)
