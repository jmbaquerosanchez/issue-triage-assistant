"""Step 4: classify every sampled issue and estimate usable duplicates per repo.

Per issue:
  marking events  = duplicate label added (and not removed later), marked_as_duplicate (not undone),
                    or the last close carrying stateReason DUPLICATE.
  marker          = maintainer   : some marking event by a human account, or by a bot acting on a
                                   slash command a maintainer posted just before (Prow-style);
                    maint_comment: no marking event, but an OWNER/MEMBER/COLLABORATOR comment says
                                   "duplicate of #N";
                    bot_only     : marking events, all by bots with no human command before them;
                    unmarked     : in the frame only through some comment text.
  original        = explicit : marked_as_duplicate canonical, duplicateOf, or "duplicate of #N" text
                               by the marker / a maintainer;
                    inferred : a #N (or same-repo issue URL) in a comment of the marker or of a
                               maintainer, within a day of the marking;
                    none.
  usable_strict   = maintainer (marking event) AND explicit original AND same repo AND original
                    opened earlier AND original is not a pull request.
  usable_main     = like usable_strict, but the marker may also be maint_comment (the ticket counts a
                    maintainer's "Duplicate of #N" comment as a marking). The headline figure.
  usable_lenient  = (maintainer OR maint_comment) AND explicit-or-inferred original AND same repo
                    AND earlier.

Output: out/04_classified.json (per issue, no comment bodies) and out/04_summary.json (per repo).
"""
import collections
import datetime as dt
import json
import math
import pathlib
import re

HERE = pathlib.Path(__file__).parent
counts = json.loads((HERE / "out" / "02_counts.json").read_text())
SAMPLES = HERE / "out" / "03_samples"

BOT_LOGIN = re.compile(
    r"(\[bot\]$|bot$|^bot|-bot|bot-|robot|github-actions|policy-service|vscodenpa|automation|-ci$|bedevere|issue-?helper)",
    re.I,
)
MAINTAINER_ASSOC = {"OWNER", "MEMBER", "COLLABORATOR"}
# Bugzilla's closing line, kept in the comments that LLVM's migration imported (attributed to the
# person who wrote them when the migration could map the account, else to llvmbot).
IMPORTED_DUP = re.compile(r"\*\*\* This bug has been marked as a duplicate of bug (?:([\w.-]+/[\w.-]+))?#(\d+)", re.I)
DUP_TEXT = re.compile(
    r"(?:\b(?:duplicate|dupe|dup)\s+of:?\s+(?:issue\s+)?|(?:^|\s)/(?:dup|dupe|duplicate)\s+(?:of\s+)?)"
    r"(?:#(\d+)|https?://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+))",
    re.I,
)
REF = re.compile(r"(?:(?<![\w/])#(\d+)\b|https?://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+))")
# slash commands that bots (Prow, msftbot, VS Code's triage actions, ...) execute for a maintainer
SLASH_CMD = re.compile(r"(?:^|\s)/(?:dup|dupe|duplicate|duplicates|triage|close|closeduplicate|label|resolve)\b", re.I)
DEDUPE_BOT_TEXT = re.compile(
    r"possible duplicate|potential duplicate|may be a duplicate|might be a duplicate|found \d+ possible|duplicate detection"
    r"|similar issues found|covered by an existing one|following (?:open )?issues? (?:may|might|could) be",
    re.I,
)


def ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


# Automation running from ordinary user accounts (actor type "User") that the regex misses, found by
# auditing the marking actors of the sample with actors.py.
KNOWN_AUTOMATION = {"robobun", "linear"}


def is_bot(actor) -> bool | None:
    if not actor:
        return None  # deleted account ("ghost")
    return (
        actor["__typename"] == "Bot"
        or bool(BOT_LOGIN.search(actor["login"]))
        or actor["login"].lower() in KNOWN_AUTOMATION
    )


def ref_from_match(m, repo):
    if m.group(1):
        return repo, int(m.group(1))
    return m.group(2), int(m.group(3))


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def classify(repo: str, issue: dict) -> dict:
    labels = set(counts[repo]["dup_labels"])
    nodes = sorted(issue["timelineItems"]["nodes"], key=lambda n: n["createdAt"])
    comments = [n for n in nodes if n["__typename"] == "IssueComment"]
    closes = [n for n in nodes if n["__typename"] == "ClosedEvent"]
    markings = []

    # labels: keep a dup-label addition only if the label is still on (no later removal)
    for i, n in enumerate(nodes):
        if n["__typename"] == "LabeledEvent" and n["label"] and n["label"]["name"] in labels:
            removed = any(
                m["__typename"] == "UnlabeledEvent" and m["label"] and m["label"]["name"] == n["label"]["name"]
                for m in nodes[i + 1 :]
            )
            if not removed:
                markings.append({"kind": "label", "at": n["createdAt"], "actor": n["actor"], "canonical": None})
    for i, n in enumerate(nodes):
        if n["__typename"] == "MarkedAsDuplicateEvent":
            # The event lives on the duplicate's timeline only. Its two sides came back reversed with
            # respect to the schema descriptions (canonical = this issue, duplicate = the original),
            # so the original is whichever side is not this issue.
            sides = [s for s in (n["canonical"], n.get("duplicate")) if s]
            others = [
                s
                for s in sides
                if not (s["number"] == issue["number"] and s["repository"]["nameWithOwner"].lower() == repo.lower())
            ]
            can = others[0] if others else None
            undone = any(m["__typename"] == "UnmarkedAsDuplicateEvent" for m in nodes[i + 1 :])
            if not undone:
                markings.append({"kind": "mad", "at": n["createdAt"], "actor": n["actor"], "canonical": can})
    if closes and closes[-1]["stateReason"] == "DUPLICATE":
        c = closes[-1]
        markings.append({"kind": "close_dup", "at": c["createdAt"], "actor": c["actor"], "canonical": c["duplicateOf"]})

    # who decided each marking
    for mk in markings:
        b = is_bot(mk["actor"])
        mk["bot"] = b
        mk["on_command"] = False
        if b is not False:  # a bot, or a deleted account (often a retired bot)
            t = ts(mk["at"])
            for c in comments:
                dtm = (t - ts(c["createdAt"])).total_seconds()
                # No authorAssociation check here: team members with private org membership show up as
                # CONTRIBUTOR (seen in microsoft/vscode), and the bot only acts for people it trusts.
                if 0 <= dtm <= 3600 and is_bot(c["author"]) is False and SLASH_CMD.search(c["body"] or ""):
                    mk["on_command"] = True
                    mk["commander_comment"] = c
                    break
            # trigger labels: a human applies e.g. `bot/duplicate` and the bot does the rest (grafana)
            for n in nodes:
                if (
                    n["__typename"] == "LabeledEvent"
                    and n["label"]
                    and re.search("dup", n["label"]["name"], re.I)
                    and is_bot(n["actor"]) is False
                    and 0 <= (t - ts(n["createdAt"])).total_seconds() <= 3600
                ):
                    mk["on_command"] = True

    # Anyone can close their own issue, so a "close as duplicate" by the issue's author is the
    # reporter's call, not a maintainer's. (Labels need triage access and marked_as_duplicate needs
    # write access, so those count whoever applies them.)
    author = (issue.get("author") or {}).get("login")
    for mk in markings:
        mk["by_author"] = mk["kind"] == "close_dup" and bool(mk["actor"]) and mk["actor"]["login"] == author
    human_marks = [m for m in markings if (m["bot"] is False or m["on_command"]) and not m["by_author"]]
    maint_dup_comments = [
        c
        for c in comments
        if c["authorAssociation"] in MAINTAINER_ASSOC and not is_bot(c["author"]) and DUP_TEXT.search(c["body"] or "")
    ]
    if human_marks:
        marker = "maintainer"
    elif markings and all(m["by_author"] for m in markings):
        marker = "author_self"
    elif markings and all(m["bot"] for m in markings):
        marker = "bot_only"
    elif markings:
        marker = "unknown_actor"  # e.g. deleted account
    elif maint_dup_comments:
        marker = "maint_comment"
    else:
        marker = "unmarked"
    imported = [c for c in comments if IMPORTED_DUP.search(c["body"] or "")]
    if marker == "unmarked" and imported:
        marker = "imported"  # a human's marking in the previous tracker, carried over by the migration

    # the original
    original, how = None, "none"
    if marker == "imported":
        m = IMPORTED_DUP.search(imported[-1]["body"])
        original = {"repo": m.group(1) or repo, "number": int(m.group(2)), "createdAt": None, "type": None}
        how = "explicit_text"
    explicit = [m["canonical"] for m in markings if m["canonical"]]
    if issue.get("duplicateOf"):
        explicit.append(dict(issue["duplicateOf"], __typename="Issue"))
    if original:
        pass
    elif explicit:
        can = explicit[-1]
        original = {
            "repo": can["repository"]["nameWithOwner"],
            "number": can["number"],
            "createdAt": can["createdAt"],
            "type": can["__typename"],
        }
        how = "explicit_event"
    else:
        deciders = {m["actor"]["login"] for m in markings if m["actor"]}
        deciders |= {m["commander_comment"]["author"]["login"] for m in markings if m.get("commander_comment")}
        # Once a marking event proves a maintainer acted, CONTRIBUTOR comments may also name the
        # original: team members with private org membership show up as CONTRIBUTOR.
        assoc = MAINTAINER_ASSOC | ({"CONTRIBUTOR"} if marker == "maintainer" else set())
        text_sources = [
            c
            for c in comments
            if c["author"]
            and (c["author"]["login"] in deciders or (c["authorAssociation"] in assoc and not is_bot(c["author"])))
        ]
        for c in text_sources:
            m = DUP_TEXT.search(c["body"] or "")
            if m and ref_from_match(m, repo) != (repo, issue["number"]):
                r, num = ref_from_match(m, repo)
                original = {"repo": r, "number": num, "createdAt": None, "type": None}
                how = "explicit_text"
                break
        if not original and markings:
            # the last same-repo reference in those comments up to a day after the first marking
            t0 = min(ts(m["at"]) for m in markings)
            for c in text_sources:
                if (ts(c["createdAt"]) - t0).total_seconds() <= 86400:
                    for m in REF.finditer(c["body"] or ""):
                        r, num = ref_from_match(m, repo)
                        if r.lower() == repo.lower() and num != issue["number"]:
                            original = {"repo": r, "number": num, "createdAt": None, "type": None}
                            how = "inferred_ref"

    same_repo = bool(original) and original["repo"].lower() == repo.lower()
    if original and original["createdAt"]:
        earlier = ts(original["createdAt"]) < ts(issue["createdAt"])
    elif original:
        earlier = same_repo and original["number"] < issue["number"]  # numbers are assigned in creation order
    else:
        earlier = False
    not_pr = bool(original) and original["type"] != "PullRequest"

    usable_strict = marker == "maintainer" and how in ("explicit_event", "explicit_text") and same_repo and earlier and not_pr
    human = ("maintainer", "maint_comment", "imported")
    usable_main = marker in human and how in ("explicit_event", "explicit_text") and same_repo and earlier and not_pr
    usable_lenient = marker in human and how != "none" and same_repo and earlier and not_pr

    first = min(markings, key=lambda m: m["at"]) if markings else None
    bot_dedupe_comments = [
        c["author"]["login"] for c in comments if is_bot(c["author"]) and DEDUPE_BOT_TEXT.search(c["body"] or "")
    ]
    return {
        "repo": repo,
        "number": issue["number"],
        "createdAt": issue["createdAt"],
        "stratum": issue["_stratum"],
        "stateReason": issue["stateReason"],
        "marking_kinds": sorted({m["kind"] for m in markings}),
        "first_marking_kind": first["kind"] if first else None,
        "first_marking_actor": (
            None
            if not first
            else ("bot:" + first["actor"]["login"] if first["bot"] else ("ghost" if first["bot"] is None else "human"))
        ),
        "first_marking_on_command": bool(first and first["on_command"]),
        "marker": marker,
        "original_how": how,
        "original": original,
        "same_repo": same_repo,
        "earlier": earlier,
        "usable_strict": usable_strict,
        "usable_main": usable_main,
        "usable_lenient": usable_lenient,
        "bot_dedupe_comments": bot_dedupe_comments,
        "timeline_truncated": issue["timelineItems"]["totalCount"] > len(issue["timelineItems"]["nodes"]),
    }


rows, summary = [], {}
for f in sorted(SAMPLES.glob("*.json")):
    d = json.loads(f.read_text())
    repo = d["repo"]
    cls = [classify(repo, i) for i in d["issues"]]
    rows += cls
    n = len(cls)
    frame = counts[repo]["union"]
    s = {"frame": frame, "n": n}
    for key in ("usable_strict", "usable_main", "usable_lenient"):
        k = sum(c[key] for c in cls)
        lo, hi = wilson(k, n)
        s[key] = {"k": k, "p": round(k / n, 3), "est": round(frame * k / n), "lo": round(frame * lo), "hi": round(frame * hi)}
    s["marker"] = dict(collections.Counter(c["marker"] for c in cls))
    s["original_how"] = dict(collections.Counter(c["original_how"] for c in cls if c["marker"] in ("maintainer", "maint_comment", "imported")))
    s["first_actor"] = dict(collections.Counter(c["first_marking_actor"] for c in cls).most_common())
    s["on_command"] = sum(c["first_marking_on_command"] for c in cls)
    s["bot_dedupe_comment_issues"] = sum(bool(c["bot_dedupe_comments"]) for c in cls)
    s["bot_dedupe_logins"] = dict(collections.Counter(l for c in cls for l in set(c["bot_dedupe_comments"])))
    s["truncated"] = sum(c["timeline_truncated"] for c in cls)
    summary[repo] = s

(HERE / "out" / "04_classified.json").write_text(json.dumps(rows, indent=0))
(HERE / "out" / "04_summary.json").write_text(json.dumps(summary, indent=1))
for repo, s in sorted(summary.items(), key=lambda kv: -kv[1]["usable_main"]["lo"]):
    us, ul, um = s["usable_strict"], s["usable_lenient"], s["usable_main"]
    print(
        f"{repo:30} frame={s['frame']:>6} n={s['n']:>3} strict={us['k']:>2} ({us['p']:.2f}) ~{us['est']} [{us['lo']}-{us['hi']}]"
        f"  MAIN={um['k']:>2} ~{um['est']} [{um['lo']}-{um['hi']}]"
        f"  lenient={ul['k']:>2} ~{ul['est']} [{ul['lo']}-{ul['hi']}]  marker={s['marker']} how={s['original_how']}"
        f" cmd={s['on_command']} dedupebot={s['bot_dedupe_comment_issues']} trunc={s['truncated']}"
    )
    print(f"{'':30} first_actor={s['first_actor']} dedupe_logins={s['bot_dedupe_logins']}")
