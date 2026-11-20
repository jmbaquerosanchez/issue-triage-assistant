"""Step 3b: add the `duplicate` side to sampled marked_as_duplicate events that lack it.

Why: on the duplicate's own timeline, GraphQL's MarkedAsDuplicateEvent returned the duplicate itself
in `canonical` and the original in `duplicate` (the reverse of the schema descriptions), e.g.
golang/go#50099 ("Duplicate of #40785"): canonical=50099, duplicate=40785. Samples fetched before
`duplicate` was added to 03_sample.py are patched here in place.
"""
import json
import pathlib
import time

from gh_graphql import graphql

HERE = pathlib.Path(__file__).parent
REF = """__typename
  ... on Issue { number createdAt repository { nameWithOwner } }
  ... on PullRequest { number createdAt repository { nameWithOwner } }"""

for f in sorted((HERE / "out" / "03_samples").glob("*.json")):
    d = json.loads(f.read_text())
    owner, name = d["repo"].split("/")
    need = [
        i
        for i in d["issues"]
        if any(n["__typename"] == "MarkedAsDuplicateEvent" and "duplicate" not in n for n in i["timelineItems"]["nodes"])
    ]
    if not need:
        continue
    for k in range(0, len(need), 20):
        chunk = need[k : k + 20]
        parts = [
            f"i{i['number']}: issue(number: {i['number']}) {{ timelineItems(first: 50, itemTypes: [MARKED_AS_DUPLICATE_EVENT]) {{"
            f" nodes {{ ... on MarkedAsDuplicateEvent {{ createdAt canonical {{ {REF} }} duplicate {{ {REF} }} }} }} }} }}"
            for i in chunk
        ]
        data = graphql(f'{{ repository(owner: "{owner}", name: "{name}") {{ {" ".join(parts)} }} }}')["data"]["repository"]
        for i in chunk:
            fetched = {e["createdAt"]: e for e in data[f"i{i['number']}"]["timelineItems"]["nodes"]}
            for n in i["timelineItems"]["nodes"]:
                if n["__typename"] == "MarkedAsDuplicateEvent" and n["createdAt"] in fetched:
                    n["duplicate"] = fetched[n["createdAt"]]["duplicate"]
        time.sleep(1)
    f.write_text(json.dumps(d))
    print(d["repo"], len(need))
