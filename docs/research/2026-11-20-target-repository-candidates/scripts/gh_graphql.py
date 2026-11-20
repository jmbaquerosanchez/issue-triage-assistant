"""Tiny helper: run a GraphQL query through the authenticated `gh` CLI (read-only)."""
import json
import subprocess
import time


def graphql(query: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        proc = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
        # gh exits non-zero on partial errors too; keep data if present
        try:
            body = json.loads(proc.stdout)
            if body.get("data"):
                return body
        except json.JSONDecodeError:
            pass
        wait = 10 * (attempt + 1)
        print(f"graphql error (attempt {attempt + 1}), retrying in {wait}s: {proc.stderr[:300]}")
        time.sleep(wait)
    raise RuntimeError(proc.stderr)


def alias(repo: str) -> str:
    return "r_" + repo.replace("/", "__").replace("-", "_").replace(".", "_")
