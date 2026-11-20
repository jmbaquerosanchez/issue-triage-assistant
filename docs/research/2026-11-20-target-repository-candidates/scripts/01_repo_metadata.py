"""Step 1: repository metadata and every label whose name contains "dup".

Output: out/01_repo_metadata.json
Cost: one GraphQL query per 10 repositories.
"""
import json
import pathlib
import time

from gh_graphql import alias, graphql

HERE = pathlib.Path(__file__).parent
repos = [r.strip() for r in (HERE / "repos.txt").read_text().splitlines() if r.strip()]

FIELDS = """
  nameWithOwner stargazerCount forkCount isArchived pushedAt createdAt hasIssuesEnabled
  homepageUrl primaryLanguage { name } licenseInfo { spdxId name }
  issues { totalCount }
  open: issues(states: OPEN) { totalCount }
  labels(query: "dup", first: 20) { nodes { name issues { totalCount } } }
"""

result = {}
for i in range(0, len(repos), 10):
    chunk = repos[i : i + 10]
    parts = []
    for r in chunk:
        owner, name = r.split("/")
        parts.append(f'{alias(r)}: repository(owner: "{owner}", name: "{name}") {{ {FIELDS} }}')
    data = graphql("{ " + "\n".join(parts) + " rateLimit { cost remaining } }")
    for r in chunk:
        result[r] = data["data"].get(alias(r))
    print(i, data["data"]["rateLimit"])
    time.sleep(1)

(HERE / "out" / "01_repo_metadata.json").write_text(json.dumps(result, indent=1))
