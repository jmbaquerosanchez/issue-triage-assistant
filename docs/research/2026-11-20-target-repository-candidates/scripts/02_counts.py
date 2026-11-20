"""Step 2: cheap search counts for every candidate (GitHub GraphQL `search`, issueCount only).

Counts, all restricted to `is:issue` (pull requests excluded):
  closed        is:closed
  reason_dup    reason:duplicate            (GitHub's "Close as duplicate" reason)
  label_dup     sum over the repo's duplicate label(s), from step 1 (Label.issues.totalCount)
  dup_comment   "duplicate of" in:comments  (the comment syntax that creates a marked_as_duplicate event)
  union         ISSUE_ADVANCED: (label:L... OR reason:duplicate OR "duplicate of" in:comments)
  closed_by_pr  is:closed linked:pr         (closed issues linked to a PR by a closing reference)
  docs_link     is:closed "<docs prefix>" in:comments  (proxy; see the research note)

Output: out/02_counts.json
"""
import json
import pathlib
import re
import time

from gh_graphql import alias, graphql

HERE = pathlib.Path(__file__).parent
meta = json.loads((HERE / "out" / "01_repo_metadata.json").read_text())

# Labels that hold "maybe" or bot output, or that are not about duplicate issues at all.
NOT_A_MARKING = re.compile(r"potential|possible|dedupe-digest|discussion-|bot/|BlockedUpstream|^duplicated$", re.I)

# One docs URL prefix per repo, as it is usually written in comments (GitHub search matches the host literally).
DOCS = {
    "microsoft/vscode": "code.visualstudio.com/docs",
    "microsoft/TypeScript": "www.typescriptlang.org/docs",
    "facebook/react": "react.dev",
    "vercel/next.js": "nextjs.org/docs",
    "angular/angular": "angular.dev",
    "vuejs/core": "vuejs.org",
    "sveltejs/svelte": "svelte.dev/docs",
    "vitejs/vite": "vite.dev",
    "nodejs/node": "nodejs.org/api",
    "denoland/deno": "docs.deno.com",
    "oven-sh/bun": "bun.sh/docs",
    "electron/electron": "www.electronjs.org/docs",
    "prettier/prettier": "prettier.io/docs",
    "eslint/eslint": "eslint.org/docs",
    "mui/material-ui": "mui.com",
    "nuxt/nuxt": "nuxt.com/docs",
    "webpack/webpack": "webpack.js.org",
    "microsoft/playwright": "playwright.dev/docs",
    "storybookjs/storybook": "storybook.js.org/docs",
    "facebook/react-native": "reactnative.dev/docs",
    "expo/expo": "docs.expo.dev",
    "golang/go": "pkg.go.dev",
    "kubernetes/kubernetes": "kubernetes.io/docs",
    "moby/moby": "docs.docker.com",
    "hashicorp/terraform": "developer.hashicorp.com/terraform",
    "hashicorp/terraform-provider-aws": "registry.terraform.io/providers/hashicorp/aws",
    "grafana/grafana": "grafana.com/docs",
    "cli/cli": "cli.github.com/manual",
    "prometheus/prometheus": "prometheus.io/docs",
    "gohugoio/hugo": "gohugo.io",
    "docker/compose": "docs.docker.com/compose",
    "ollama/ollama": "ollama/blob/main/docs",
    "rust-lang/rust": "doc.rust-lang.org",
    "rust-lang/rust-analyzer": "rust-analyzer.github.io",
    "rust-lang/cargo": "doc.rust-lang.org/cargo",
    "zed-industries/zed": "zed.dev/docs",
    "tauri-apps/tauri": "tauri.app",
    "bevyengine/bevy": "docs.rs/bevy",
    "alacritty/alacritty": "alacritty.org",
    "astral-sh/uv": "docs.astral.sh/uv",
    "astral-sh/ruff": "docs.astral.sh/ruff",
    "python/cpython": "docs.python.org",
    "pandas-dev/pandas": "pandas.pydata.org",
    "numpy/numpy": "numpy.org/doc",
    "matplotlib/matplotlib": "matplotlib.org",
    "scikit-learn/scikit-learn": "scikit-learn.org",
    "pytorch/pytorch": "pytorch.org/docs",
    "tensorflow/tensorflow": "www.tensorflow.org",
    "home-assistant/core": "www.home-assistant.io",
    "ansible/ansible": "docs.ansible.com",
    "pypa/pip": "pip.pypa.io",
    "python/mypy": "mypy.readthedocs.io",
    "microsoft/pyright": "pyright/blob/main/docs",
    "huggingface/transformers": "huggingface.co/docs/transformers",
    "langchain-ai/langchain": "python.langchain.com",
    "godotengine/godot": "docs.godotengine.org",
    "neovim/neovim": "neovim.io/doc",
    "microsoft/terminal": "learn.microsoft.com",
    "microsoft/PowerToys": "learn.microsoft.com",
    "microsoft/WSL": "learn.microsoft.com",
    "obsproject/obs-studio": "obsproject.com/kb",
    "llvm/llvm-project": "llvm.org/docs",
    "dotnet/runtime": "learn.microsoft.com",
    "dotnet/roslyn": "learn.microsoft.com",
    "dotnet/aspnetcore": "learn.microsoft.com",
    "PowerShell/PowerShell": "learn.microsoft.com",
    "microsoft/winget-cli": "learn.microsoft.com",
    "flutter/flutter": "docs.flutter.dev",
    "dart-lang/sdk": "dart.dev",
    "elastic/elasticsearch": "www.elastic.co/guide",
    "spring-projects/spring-boot": "docs.spring.io/spring-boot",
    "keycloak/keycloak": "www.keycloak.org/docs",
    "rails/rails": "guides.rubyonrails.org",
    "mastodon/mastodon": "docs.joinmastodon.org",
    "Homebrew/brew": "docs.brew.sh",
    "JuliaLang/julia": "docs.julialang.org",
    "ziglang/zig": "ziglang.org/documentation",
    "NixOS/nixpkgs": "nixos.org/manual",
    "ohmyzsh/ohmyzsh": "ohmyzsh/wiki",
    "desktop/desktop": "docs.github.com/en/desktop",
    "anthropics/claude-code": "docs.anthropic.com",
    "openai/codex": "codex/blob/main/docs",
    "immich-app/immich": "immich.app/docs",
    "nextcloud/server": "docs.nextcloud.com",
    "jellyfin/jellyfin": "jellyfin.org/docs",
}


def q(s: str) -> str:
    return json.dumps(s)


out_path = HERE / "out" / "02_counts.json"
result = json.loads(out_path.read_text()) if out_path.exists() else {}
todo = [r for r in meta if r not in result]

for i in range(0, len(todo), 3):
    chunk = todo[i : i + 3]
    parts = []
    labels_by_repo = {}
    for r in chunk:
        a = alias(r)
        base = f"repo:{r} is:issue"
        labels = [
            l["name"] for l in meta[r]["labels"]["nodes"] if not NOT_A_MARKING.search(l["name"]) and l["issues"]["totalCount"] > 0
        ]
        labels_by_repo[r] = labels
        or_terms = [f'label:"{l}"' for l in labels] + ["reason:duplicate", '"duplicate of" in:comments']
        searches = {
            "closed": ("ISSUE", f"{base} is:closed"),
            "reason_dup": ("ISSUE", f"{base} reason:duplicate"),
            "dup_comment": ("ISSUE", f'{base} "duplicate of" in:comments'),
            "union": ("ISSUE_ADVANCED", f"{base} ({' OR '.join(or_terms)})"),
            "closed_by_pr": ("ISSUE", f"{base} is:closed linked:pr"),
            "docs_link": ("ISSUE", f'{base} is:closed "{DOCS[r]}" in:comments'),
        }
        for key, (typ, query) in searches.items():
            parts.append(f"{a}__{key}: search(type: {typ}, query: {q(query)}) {{ issueCount }}")
    data = graphql("{ " + "\n".join(parts) + " rateLimit { cost remaining } }")["data"]
    for r in chunk:
        a = alias(r)
        row = {k[len(a) + 2 :]: v["issueCount"] for k, v in data.items() if k.startswith(a + "__")}
        row["dup_labels"] = labels_by_repo[r]
        row["label_dup"] = sum(
            l["issues"]["totalCount"] for l in meta[r]["labels"]["nodes"] if l["name"] in labels_by_repo[r]
        )
        row["docs_prefix"] = DOCS[r]
        result[r] = row
    print(i, data["rateLimit"])
    out_path.write_text(json.dumps(result, indent=1))
    time.sleep(2)
