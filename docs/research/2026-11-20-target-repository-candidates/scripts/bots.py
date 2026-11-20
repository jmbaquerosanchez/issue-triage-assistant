"""Audit helper: comments in the sample by bot accounts that suggest or announce duplicates.

Prints, per repo, the bot login, how many sampled issues carry such a comment, and one excerpt.
"""
import collections
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
spec_src = (HERE / "04_classify.py").read_text()
BOT = re.compile(
    r"(\[bot\]$|bot$|^bot|-bot|bot-|robot|github-actions|policy-service|vscodenpa|automation|-ci$|bedevere|issue-?helper|^robobun$)",
    re.I,
)
DUPE = re.compile(r"duplicate|similar issue|same (?:bug|request|problem|issue) (?:as|tracked)", re.I)
for f in sorted((HERE / "out" / "03_samples").glob("*.json")):
    d = json.loads(f.read_text())
    seen = collections.defaultdict(set)
    excerpt, first = {}, {}
    for i in d["issues"]:
        for n in i["timelineItems"]["nodes"]:
            if n["__typename"] != "IssueComment" or not n["author"]:
                continue
            a = n["author"]
            body = n["body"] or ""
            if (a["__typename"] == "Bot" or BOT.search(a["login"])) and DUPE.search(body):
                if "locked since" in body or "automatically locked" in body:
                    continue
                seen[a["login"]].add(i["number"])
                excerpt.setdefault(a["login"], " ".join(body.split())[:140])
                first[a["login"]] = min(first.get(a["login"], n["createdAt"]), n["createdAt"])
    for login, nums in seen.items():
        print(f"{d['repo']:28} {login:34} {len(nums):>2}/{len(d['issues'])} since {first[login][:7]}  {excerpt[login]}")
