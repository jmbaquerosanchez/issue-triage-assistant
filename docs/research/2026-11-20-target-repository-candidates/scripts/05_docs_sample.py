"""Step 5: how many of the docs_link hits of step 2 are a maintainer's closing comment linking the docs.

Frame: `is:issue is:closed "<docs prefix>" in:comments` (step 2's docs_link).
Sample: N_SAMPLE issues per repo, from random date windows across the repo's life (2 per window).
An issue counts when a comment by OWNER/MEMBER/COLLABORATOR (not a bot) that contains the docs prefix
was posted within 24 hours before the issue's last close.

Usage: python3 05_docs_sample.py owner/name [owner/name ...]
Output: out/05_docs_sample.json (no comment bodies).
"""
import datetime as dt
import json
import pathlib
import random
import re
import sys
import time

from gh_graphql import graphql

HERE = pathlib.Path(__file__).parent
meta = json.loads((HERE / "out" / "01_repo_metadata.json").read_text())
counts = json.loads((HERE / "out" / "02_counts.json").read_text())
N_SAMPLE = 20
TODAY = dt.date(2026, 11, 20)
BOT_LOGIN = re.compile(r"(\[bot\]$|bot$|^bot|-bot|bot-|robot|github-actions|policy-service|vscodenpa)", re.I)
FIELDS = """... on Issue { number closedAt
  timelineItems(last: 60, itemTypes: [ISSUE_COMMENT, CLOSED_EVENT]) { nodes { __typename
    ... on ClosedEvent { createdAt }
    ... on IssueComment { createdAt authorAssociation author { login __typename } body } } } }"""

out_path = HERE / "out" / "05_docs_sample.json"
result = json.loads(out_path.read_text()) if out_path.exists() else {}
for repo in sys.argv[1:]:
    prefix = counts[repo]["docs_prefix"]
    rng = random.Random("docs:" + repo)
    start = dt.date.fromisoformat(meta[repo]["createdAt"][:10])
    span = (TODAY - start).days
    windows = sorted(start + dt.timedelta(days=rng.randrange(span)) for _ in range(N_SAMPLE // 2))
    issues = {}
    for i in range(0, len(windows), 5):
        parts = []
        for j, d in enumerate(windows[i : i + 5]):
            q = f'repo:{repo} is:issue is:closed "{prefix}" in:comments created:>={d.isoformat()} sort:created-asc'
            parts.append(f"w{j}: search(type: ISSUE, first: 2, query: {json.dumps(q)}) {{ nodes {{ {FIELDS} }} }}")
        data = graphql("{ " + " ".join(parts) + " }")["data"]
        for j in range(len(windows[i : i + 5])):
            for n in data[f"w{j}"]["nodes"]:
                issues.setdefault(n["number"], n)
        time.sleep(1)
    rows = []
    for n in issues.values():
        nodes = n["timelineItems"]["nodes"]
        closes = [x for x in nodes if x["__typename"] == "ClosedEvent"]
        if not closes:
            continue
        t_close = dt.datetime.fromisoformat(closes[-1]["createdAt"].replace("Z", "+00:00"))
        hit = any(
            x["__typename"] == "IssueComment"
            and x["author"]
            and x["authorAssociation"] in ("OWNER", "MEMBER", "COLLABORATOR")
            and not (x["author"]["__typename"] == "Bot" or BOT_LOGIN.search(x["author"]["login"]))
            and prefix.lower() in (x["body"] or "").lower()
            and 0 <= (t_close - dt.datetime.fromisoformat(x["createdAt"].replace("Z", "+00:00"))).total_seconds() <= 86400
            for x in nodes
        )
        rows.append({"number": n["number"], "maintainer_closing_docs_link": hit})
    k = sum(r["maintainer_closing_docs_link"] for r in rows)
    result[repo] = {"prefix": prefix, "frame": counts[repo]["docs_link"], "n": len(rows), "k": k, "rows": rows}
    print(repo, prefix, f"frame={counts[repo]['docs_link']} n={len(rows)} k={k} est~{round(counts[repo]['docs_link'] * k / max(len(rows), 1))}")
    out_path.write_text(json.dumps(result, indent=1))
