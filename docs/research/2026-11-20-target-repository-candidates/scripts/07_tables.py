"""Step 7: render the Markdown tables of the research note from out/*.json."""
import json
import pathlib

HERE = pathlib.Path(__file__).parent
meta = json.loads((HERE / "out" / "01_repo_metadata.json").read_text())
counts = json.loads((HERE / "out" / "02_counts.json").read_text())
summary = json.loads((HERE / "out" / "04_summary.json").read_text())
docs = json.loads((HERE / "out" / "05_docs_sample.json").read_text())

# Checked by hand against each repo's root contents and its separate website repo (see the note).
DOCS_IN_REPO = {
    "microsoft/vscode": "no (microsoft/vscode-docs)",
    "microsoft/PowerToys": "no (`doc/` = dev docs, specs)",
    "flutter/flutter": "no (flutter/website; `docs/` = contributor docs)",
    "godotengine/godot": "partly (class reference in `doc/`; manual in godot-docs)",
    "microsoft/terminal": "no (MicrosoftDocs/terminal)",
    "llvm/llvm-project": "yes (`llvm/docs`, `clang/docs`, ...)",
    "anthropics/claude-code": "no (product source and docs not in repo)",
    "oven-sh/bun": "yes (`docs/`)",
    "golang/go": "partly (`doc/` = spec, release notes; site in golang/website)",
    "dotnet/runtime": "no (dotnet/docs, dotnet-api-docs; `docs/` = design)",
    "microsoft/TypeScript": "no (microsoft/TypeScript-Website)",
    "home-assistant/core": "no (home-assistant/home-assistant.io)",
    "dart-lang/sdk": "no (dart-lang/site-www; `docs/` = contributor)",
    "dotnet/roslyn": "no (user docs in dotnet/docs; `docs/` = compiler notes)",
    "mui/material-ui": "yes (`docs/`)",
    "rust-lang/rust": "partly (`src/doc`; std docs in source; the Book is rust-lang/book)",
    "openai/codex": "yes (`docs/`)",
    "python/cpython": "yes (`Doc/`)",
    "angular/angular": "yes (`adev/` = angular.dev)",
    "zed-industries/zed": "yes (`docs/`)",
    "dotnet/aspnetcore": "no (dotnet/AspNetCore.Docs; `docs/` = contributor)",
    "spring-projects/spring-boot": "yes (`documentation/`)",
    "grafana/grafana": "yes (`docs/sources`)",
    "pandas-dev/pandas": "yes (`doc/`)",
    "kubernetes/kubernetes": "no (kubernetes/website)",
    "vercel/next.js": "yes (`docs/`)",
    "pytorch/pytorch": "yes, API reference (`docs/source`)",
    "microsoft/WSL": "no (MicrosoftDocs/wsl)",
    "nextcloud/server": "no (nextcloud/documentation)",
}


def lic(r):
    li = meta[r]["licenseInfo"]
    return li["spdxId"] if li else "none"


def k(n):
    return f"{n / 1000:.0f}k" if n >= 10000 else f"{n / 1000:.1f}k" if n >= 1000 else str(n)


print("## Sampled candidates\n")
print(
    "| Repository | Stars | Issues | License | Frame | n | Usable, explicit original (95% CI) | + inferred original | "
    "Marked only by a bot (in sample) | Closed by a PR | Docs-link comments (proxy) | Docs in the repo |"
)
print("|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---|")
for r, s in sorted(summary.items(), key=lambda kv: -kv[1]["usable_main"]["lo"]):
    m, l = s["usable_main"], s["usable_lenient"]
    bot = s["marker"].get("bot_only", 0)
    d = docs.get(r)
    docs_cell = f"{counts[r]['docs_link']:,}" + (f" ({d['k']}/{d['n']} maintainer closing)" if d else "")
    print(
        f"| {r} | {k(meta[r]['stargazerCount'])} | {meta[r]['issues']['totalCount']:,} | {lic(r)} | {s['frame']:,} | {s['n']} | "
        f"**~{m['est']:,}** ({m['lo']:,}–{m['hi']:,}) | ~{l['est']:,} | {bot}/{s['n']} | {counts[r]['closed_by_pr']:,} | "
        f"{docs_cell} | {DOCS_IN_REPO.get(r, '?')} |"
    )

print("\n## How each sampled issue was marked\n")
print("| Repository | Maintainer event | Maintainer comment only | Imported | Bot only | Author self-close | Deleted account | Not marked | Original named explicitly / inferred / none |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---|")
for r, s in sorted(summary.items(), key=lambda kv: -kv[1]["usable_main"]["lo"]):
    mk, how = s["marker"], s["original_how"]
    expl = how.get("explicit_event", 0) + how.get("explicit_text", 0)
    print(
        f"| {r} | {mk.get('maintainer', 0)} | {mk.get('maint_comment', 0)} | {mk.get('imported', 0)} | {mk.get('bot_only', 0)} | "
        f"{mk.get('author_self', 0)} | {mk.get('unknown_actor', 0)} | {mk.get('unmarked', 0)} | {expl} / {how.get('inferred_ref', 0)} / {how.get('none', 0)} |"
    )

print("\n## All candidates: search counts\n")
print("| Repository | Stars | Issues | License | Duplicate label(s): issues | `reason:duplicate` | `\"duplicate of\"` in comments | Frame (union) | Closed, linked PR | Docs-link comments (prefix) |")
print("|---|---:|---:|---|---|---:|---:|---:|---:|---|")
for r, c in sorted(counts.items(), key=lambda kv: -kv[1]["union"]):
    labels = ", ".join(f"`{l['name']}`: {l['issues']['totalCount']:,}" for l in meta[r]["labels"]["nodes"] if l["name"] in c["dup_labels"]) or "—"
    if c["closed"] == 0:  # the search API refused the repo (HTTP 422), see the note
        print(f"| {r} | {k(meta[r]['stargazerCount'])} | {meta[r]['issues']['totalCount']:,} | {lic(r)} | {labels} | n/a | n/a | n/a | n/a | n/a |")
        continue
    print(
        f"| {r} | {k(meta[r]['stargazerCount'])} | {meta[r]['issues']['totalCount']:,} | {lic(r)} | {labels} | {c['reason_dup']:,} | "
        f"{c['dup_comment']:,} | {c['union']:,} | {c['closed_by_pr']:,} | {c['docs_link']:,} (`{c['docs_prefix']}`) |"
    )
