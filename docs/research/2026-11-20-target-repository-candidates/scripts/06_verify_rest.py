"""Step 6: check that the GraphQL timelines of step 3 did not silently drop items, against REST.

Research #4 found that large GraphQL pages can drop timeline items without an error. Step 3 used
small pages (2 issues per search, 100 timeline items each). Here, for 2 issues per repo (the one with
the longest sampled timeline, and one at random), the counts per event type are compared with the
REST timeline endpoint (GET /repos/{owner}/{repo}/issues/{n}/timeline, paginated).

Output: out/06_verify_rest.json
"""
import collections
import json
import pathlib
import random
import subprocess

HERE = pathlib.Path(__file__).parent
GQL_TO_REST = {
    "LabeledEvent": "labeled",
    "UnlabeledEvent": "unlabeled",
    "MarkedAsDuplicateEvent": "marked_as_duplicate",
    "UnmarkedAsDuplicateEvent": "unmarked_as_duplicate",
    "ClosedEvent": "closed",
    "ReopenedEvent": "reopened",
    "IssueComment": "commented",
}
rng = random.Random(6)
report = []
for f in sorted((HERE / "out" / "03_samples").glob("*.json")):
    d = json.loads(f.read_text())
    issues = sorted(d["issues"], key=lambda i: -len(i["timelineItems"]["nodes"]))
    picks = [issues[0], rng.choice(issues[1:])]
    for i in picks:
        gql = collections.Counter(GQL_TO_REST[n["__typename"]] for n in i["timelineItems"]["nodes"])
        proc = subprocess.run(
            ["gh", "api", "--paginate", f"repos/{d['repo']}/issues/{i['number']}/timeline?per_page=100", "--jq", ".[].event"],
            capture_output=True,
            text=True,
            check=True,
        )
        rest = collections.Counter(e for e in proc.stdout.split() if e in GQL_TO_REST.values())
        diff = {k: (gql.get(k, 0), rest.get(k, 0)) for k in set(gql) | set(rest) if gql.get(k, 0) != rest.get(k, 0)}
        report.append({"repo": d["repo"], "number": i["number"], "gql_items": sum(gql.values()), "rest_items": sum(rest.values()), "diff": diff})
        print(d["repo"], i["number"], sum(gql.values()), sum(rest.values()), diff or "same")
(HERE / "out" / "06_verify_rest.json").write_text(json.dumps(report, indent=1))
