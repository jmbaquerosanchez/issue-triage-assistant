#!/usr/bin/env bash
# Per-year issue counts and issue-number ranges (issues + PRs) for godotengine/godot.
set -euo pipefail
out="$1"
echo "year,issues,first,last" > "$out"
for y in $(seq 2014 2026); do
  r="created:${y}-01-01..${y}-12-31"
  n=$(gh api -X GET search/issues -f q="repo:godotengine/godot is:issue $r" -f per_page=1 --jq .total_count)
  f=$(gh api -X GET search/issues -f q="repo:godotengine/godot $r" -f per_page=1 -f sort=created -f order=asc --jq '.items[0].number')
  l=$(gh api -X GET search/issues -f q="repo:godotengine/godot $r" -f per_page=1 -f sort=created -f order=desc --jq '.items[0].number')
  echo "$y,$n,$f,$l" | tee -a "$out"
  sleep 6.5
done
