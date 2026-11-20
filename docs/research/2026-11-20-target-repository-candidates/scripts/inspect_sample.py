"""Debug helper: print the timeline of sampled issues of a repo that fall in a given class.

Usage: python3 inspect_sample.py <owner/name> <field>=<value> [max]
  e.g. python3 inspect_sample.py golang/go marker=maint_comment 3
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
repo, cond = sys.argv[1], sys.argv[2]
nmax = int(sys.argv[3]) if len(sys.argv) > 3 else 3
field, value = cond.split("=", 1)
rows = {(r["repo"], r["number"]): r for r in json.loads((HERE / "out" / "04_classified.json").read_text())}
d = json.loads((HERE / "out" / "03_samples" / (repo.replace("/", "__") + ".json")).read_text())
k = 0
for i in d["issues"]:
    r = rows[(repo, i["number"])]
    if str(r.get(field)) != value or k >= nmax:
        continue
    k += 1
    print("===", repo, "#", i["number"], i["stateReason"], "->", r["original"], r["original_how"], "strict", r["usable_strict"])
    for n in sorted(i["timelineItems"]["nodes"], key=lambda n: n["createdAt"]):
        body = (n.get("body") or "")[:150].replace("\n", " | ")
        who = (n.get("actor") or n.get("author") or {}).get("login")
        extra = (n.get("label") or {}).get("name", "") + str(n.get("stateReason") or "")
        if n["__typename"] == "MarkedAsDuplicateEvent":
            extra = "canonical=" + str((n.get("canonical") or {}).get("number"))
        print("  ", n["createdAt"][:16], n["__typename"][:14], who, n.get("authorAssociation", ""), extra, body)
