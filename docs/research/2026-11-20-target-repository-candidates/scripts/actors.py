"""Audit helper: which accounts made the marking events the classifier counted as human, per repo.

Prints only accounts with 2+ markings in the sample, to eyeball automation running from ordinary user
accounts (actor type "User"), which the login regex of 04_classify.py might miss.
"""
import collections
import json
import pathlib

HERE = pathlib.Path(__file__).parent
counts = json.loads((HERE / "out" / "02_counts.json").read_text())

for f in sorted((HERE / "out" / "03_samples").glob("*.json")):
    d = json.loads(f.read_text())
    repo = d["repo"]
    labels = set(counts[repo]["dup_labels"])
    c = collections.Counter()
    for i in d["issues"]:
        for n in i["timelineItems"]["nodes"]:
            t = n["__typename"]
            is_mark = (
                (t == "LabeledEvent" and n["label"] and n["label"]["name"] in labels)
                or t == "MarkedAsDuplicateEvent"
                or (t == "ClosedEvent" and n["stateReason"] == "DUPLICATE")
            )
            if is_mark and n["actor"]:
                c[(n["actor"]["login"], n["actor"]["__typename"])] += 1
    print(repo, [f"{l}({ty[0]}):{k}" for (l, ty), k in c.most_common() if k >= 2])
