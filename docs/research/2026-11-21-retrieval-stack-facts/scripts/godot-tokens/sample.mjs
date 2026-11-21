// Stratified random sample of godotengine/godot issues (not PRs) by creation year.
// Usage: node sample.mjs <years.csv> <out.json> [perYear] [seed]
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const [yearsCsv, outPath, perYearArg, seedArg] = process.argv.slice(2);
const PER_YEAR = Number(perYearArg ?? 23);
let seed = Number(seedArg ?? 20261121) >>> 0;
function rand() { // mulberry32
  seed = (seed + 0x6D2B79F5) >>> 0;
  let t = seed;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function gql(query, variables = {}) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const r = spawnSync('gh', ['api', 'graphql', '--input', '-'], {
      input: JSON.stringify({ query, variables }), maxBuffer: 1 << 28, encoding: 'utf8',
    });
    let j;
    try { j = JSON.parse(r.stdout); } catch { j = null; }
    if (j && j.data) return j;
    console.error('graphql retry', attempt, (r.stderr || '').slice(0, 200), JSON.stringify(j?.errors ?? '').slice(0, 200));
    await sleep(5000 * (attempt + 1));
  }
  throw new Error('graphql failed');
}

const years = readFileSync(yearsCsv, 'utf8').trim().split('\n').slice(1).map((l) => {
  const [year, issues, first, last] = l.split(',').map(Number);
  return { year, issues, first, last };
});

const REPO = 'repository(owner:"godotengine", name:"godot")';
const accepted = [];
let probes = 0, prs = 0, missing = 0, wrongYear = 0;
for (const y of years) {
  // random permutation of the number range (partial Fisher-Yates on demand)
  const nums = [];
  for (let n = y.first; n <= y.last; n++) nums.push(n);
  for (let i = nums.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [nums[i], nums[j]] = [nums[j], nums[i]]; }
  const got = [];
  let idx = 0;
  while (got.length < PER_YEAR && idx < nums.length) {
    const batch = nums.slice(idx, idx + 40); idx += batch.length;
    const q = `query { ${REPO} { ${batch.map((n) => `n${n}: issueOrPullRequest(number:${n}) { __typename ... on Issue { number createdAt } }`).join('\n')} } }`;
    const j = await gql(q);
    for (const n of batch) {
      if (got.length >= PER_YEAR) break;
      probes++;
      const node = j.data.repository?.[`n${n}`];
      if (!node) { missing++; continue; }
      if (node.__typename !== 'Issue') { prs++; continue; }
      if (new Date(node.createdAt).getUTCFullYear() !== y.year) { wrongYear++; continue; }
      got.push(n);
    }
  }
  console.error(y.year, 'accepted', got.length);
  for (const n of got) accepted.push({ number: n, year: y.year });
}
console.error({ probes, prs, missing, wrongYear });

const COMMENT_FIELDS = 'totalCount pageInfo { hasNextPage endCursor } nodes { body author { __typename login } }';
const isBot = (a) => !!a && (a.__typename === 'Bot' || /\[bot\]$/.test(a.login ?? ''));
const out = [];
for (let i = 0; i < accepted.length; i += 10) {
  const batch = accepted.slice(i, i + 10);
  const q = `query { ${REPO} { ${batch.map((b) => `i${b.number}: issue(number:${b.number}) { number title body createdAt comments(first:100) { ${COMMENT_FIELDS} } }`).join('\n')} } }`;
  const j = await gql(q);
  for (const b of batch) {
    const iss = j.data.repository[`i${b.number}`];
    const comments = iss.comments.nodes.map((c) => ({ body: c.body ?? '', isBot: isBot(c.author) }));
    let pi = iss.comments.pageInfo;
    while (pi.hasNextPage) {
      const q2 = `query($n:Int!,$after:String) { ${REPO} { issue(number:$n) { comments(first:100, after:$after) { ${COMMENT_FIELDS} } } } }`;
      const j2 = await gql(q2, { n: b.number, after: pi.endCursor });
      const c2 = j2.data.repository.issue.comments;
      comments.push(...c2.nodes.map((c) => ({ body: c.body ?? '', isBot: isBot(c.author) })));
      pi = c2.pageInfo;
    }
    out.push({ number: iss.number, year: b.year, createdAt: iss.createdAt, title: iss.title ?? '', body: iss.body ?? '',
      commentCount: iss.comments.totalCount, comments });
  }
  console.error('fetched', out.length);
}
writeFileSync(outPath, JSON.stringify(out));
console.error('done', out.length, 'issues,', out.reduce((s, x) => s + x.comments.length, 0), 'comments');
