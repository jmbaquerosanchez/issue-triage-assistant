// Token statistics for the sampled godot issues with two tokenizers.
// Usage: node analyze.mjs <pkgDir> <hfCache> <years.csv> <sample.json> <out.json>
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';

const [pkg, cache, yearsCsv, samplePath, outPath] = process.argv.slice(2);
const req = createRequire(pkg + '/package.json');
const mod = await import(req.resolve('@huggingface/transformers'));
const { AutoTokenizer, env } = mod.AutoTokenizer ? mod : mod.default;
env.cacheDir = cache;

const TOTAL_ISSUES = 64503;
const years = Object.fromEntries(readFileSync(yearsCsv, 'utf8').trim().split('\n').slice(1).map((l) => {
  const [year, issues] = l.split(',').map(Number); return [year, issues];
}));
const sample = JSON.parse(readFileSync(samplePath, 'utf8'));
const nPerYear = {};
for (const s of sample) nPerYear[s.year] = (nPerYear[s.year] ?? 0) + 1;
const scale = TOTAL_ISSUES / Object.values(years).reduce((a, b) => a + b, 0);
const wOf = (y) => (years[y] * scale) / nPerYear[y]; // issues represented by one sampled issue

// Split markdown into fenced-code and other segments; also pull out HTML comments from the other text.
function segments(md) {
  const lines = md.split(/\r?\n/);
  const fenced = [], other = [];
  let inside = false, marker = '';
  for (const line of lines) {
    const m = line.match(/^\s{0,3}(`{3,}|~{3,})/);
    if (!inside && m) { inside = true; marker = m[1][0]; fenced.push(line); continue; }
    if (inside) { fenced.push(line); if (m && m[1][0] === marker) inside = false; continue; }
    other.push(line);
  }
  const otherText = other.join('\n');
  const htmlComments = (otherText.match(/<!--[\s\S]*?-->/g) ?? []).join('\n');
  return { fenced: fenced.join('\n'), other: otherText.replace(/<!--[\s\S]*?-->/g, ''), htmlComments };
}

const stackRe = /(^|\n)\s*(\[\d+\]|#\d+\s+0x|at:? .*\(.*:\d+\)|ERROR: |SCRIPT ERROR|handle_crash|Traceback|Exception|=+ (CRASH|Thread))/;
function features(body) {
  return {
    templateOld: /\*\*(Godot version|OS\/device including version|Issue description|Steps to reproduce)/i.test(body),
    templateForm: /###\s+(Tested versions|Godot version|System information|Issue description|Steps to reproduce)/i.test(body),
    hasFence: /^\s{0,3}(```|~~~)/m.test(body),
    hasHtmlComment: /<!--/.test(body),
    hasStack: stackRe.test(body),
  };
}

const quant = (pairs, q) => { // weighted quantile, pairs = [[value, weight]]
  const s = [...pairs].sort((a, b) => a[0] - b[0]);
  const tot = s.reduce((a, p) => a + p[1], 0);
  let acc = 0;
  for (const [v, w] of s) { acc += w; if (acc >= q * tot) return v; }
  return s[s.length - 1][0];
};
const wmean = (pairs, f = (x) => x) => pairs.reduce((a, [v, w]) => a + f(v) * w, 0) / pairs.reduce((a, p) => a + p[1], 0);
function dist(pairs, overs, caps) {
  const r = { n: pairs.length, mean: wmean(pairs), median: quant(pairs, 0.5), p90: quant(pairs, 0.9), p99: quant(pairs, 0.99), max: Math.max(...pairs.map((p) => p[0])) };
  for (const o of overs) r[`over${o}`] = wmean(pairs, (v) => (v > o ? 1 : 0));
  for (const c of caps) r[`cap${c}`] = wmean(pairs, (v) => Math.min(v, c));
  return r;
}

const results = { meta: { sampled: sample.length, comments: sample.reduce((a, s) => a + s.comments.length, 0), totalIssues: TOTAL_ISSUES, years, nPerYear } };
for (const id of ['Xenova/bge-small-en-v1.5', 'onnx-community/granite-embedding-small-english-r2-ONNX']) {
  const tok = await AutoTokenizer.from_pretrained(id);
  const count = (t) => (t ? tok.encode(t, { add_special_tokens: false }).length : 0);
  const rows = sample.map((s) => {
    const issueTok = count(`${s.title}\n\n${s.body}`);
    const seg = segments(s.body);
    const human = s.comments.filter((c) => !c.isBot).map((c) => count(c.body));
    return { year: s.year, w: wOf(s.year), issueTok, bodyTok: count(s.body), fencedTok: count(seg.fenced), otherTok: count(seg.other), htmlTok: count(seg.htmlComments),
      commentCount: s.comments.length, botCount: s.comments.filter((c) => c.isBot).length, human, ...features(s.body) };
  });
  const R = {};
  for (const weighted of [true, false]) {
    const W = (r) => (weighted ? r.w : 1);
    const ip = rows.map((r) => [r.issueTok, W(r)]);
    const cp = rows.flatMap((r) => r.human.map((t) => [t, W(r)]));
    const cpi = rows.map((r) => [r.commentCount, W(r)]);
    const allC = rows.reduce((a, r) => a + r.commentCount * W(r), 0);
    const botC = rows.reduce((a, r) => a + r.botCount * W(r), 0);
    const seg = ['fencedTok', 'otherTok', 'htmlTok'].map((k) => rows.reduce((a, r) => a + r[k] * W(r), 0));
    const segTot = seg.reduce((a, b) => a + b, 0);
    const share = (k) => wmean(rows.map((r) => [r[k] ? 1 : 0, W(r)]));
    R[weighted ? 'weighted' : 'unweighted'] = {
      issues: dist(ip, [256, 512, 1024, 2048, 8192], [256, 512, 1024, 2048]),
      commentsPerIssue: { mean: wmean(cpi), median: quant(cpi, 0.5), p90: quant(cpi, 0.9), max: Math.max(...cpi.map((p) => p[0])) },
      botShare: botC / allC,
      humanComments: dist(cp, [256, 512, 1024], [256, 512]),
      structure: { fencedShare: seg[0] / segTot, htmlCommentShare: seg[2] / segTot, issuesWithFence: share('hasFence'), issuesWithHtmlComment: share('hasHtmlComment'),
        issuesWithStack: share('hasStack'), templateOld: share('templateOld'), templateForm: share('templateForm') },
    };
  }
  // Extrapolation: stratified by year (sum over years of N_y * mean_y), plus naive.
  const perYear = {};
  for (const y of Object.keys(years).map(Number)) {
    const yr = rows.filter((r) => r.year === y);
    const m = (f) => yr.reduce((a, r) => a + f(r), 0) / yr.length;
    perYear[y] = { n: yr.length, N: years[y], meanIssue: m((r) => r.issueTok), medianIssue: quant(yr.map((r) => [r.issueTok, 1]), 0.5),
      meanCap512: m((r) => Math.min(r.issueTok, 512)), fencedShare: yr.reduce((a, r) => a + r.fencedTok, 0) / yr.reduce((a, r) => a + r.fencedTok + r.otherTok + r.htmlTok, 0),
      htmlShare: yr.reduce((a, r) => a + r.htmlTok, 0) / yr.reduce((a, r) => a + r.fencedTok + r.otherTok + r.htmlTok, 0),
      templateOld: m((r) => (r.templateOld ? 1 : 0)), templateForm: m((r) => (r.templateForm ? 1 : 0)),
      commentsPerIssue: m((r) => r.commentCount), humanTokPerIssue: m((r) => r.human.reduce((a, b) => a + b, 0)) };
  }
  const totals = (rs) => {
    const t = { issues: 0, issuesCap512: 0, issuesCap2048: 0, comments: 0, humanComments: 0, humanTok: 0, humanTokCap512: 0 };
    for (const r of rs) {
      t.issues += r.w * r.issueTok; t.issuesCap512 += r.w * Math.min(r.issueTok, 512); t.issuesCap2048 += r.w * Math.min(r.issueTok, 2048);
      t.comments += r.w * r.commentCount; t.humanComments += r.w * r.human.length;
      t.humanTok += r.w * r.human.reduce((a, b) => a + b, 0); t.humanTokCap512 += r.w * r.human.reduce((a, b) => a + Math.min(b, 512), 0);
    }
    return t;
  };
  const point = totals(rows);
  const naive = totals(rows.map((r) => ({ ...r, w: TOTAL_ISSUES / rows.length })));
  // Stratified bootstrap (resample within year) for 90% intervals.
  let seed = 7;
  const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
  const byYear = {};
  for (const r of rows) (byYear[r.year] ??= []).push(r);
  const boots = [];
  for (let b = 0; b < 2000; b++) {
    const rs = [];
    for (const yr of Object.values(byYear)) for (let i = 0; i < yr.length; i++) rs.push(yr[Math.floor(rnd() * yr.length)]);
    boots.push(totals(rs));
  }
  const ci = {};
  for (const k of Object.keys(point)) {
    const v = boots.map((t) => t[k]).sort((a, b) => a - b);
    ci[k] = [v[Math.floor(0.05 * v.length)], v[Math.floor(0.95 * v.length)]];
  }
  // Longest issues: what inflates them.
  const top = [...rows].map((r, i) => ({ ...r, i })).sort((a, b) => b.issueTok - a.issueTok).slice(0, 8)
    .map((r) => ({ year: r.year, tok: r.issueTok, fencedPct: Math.round((100 * r.fencedTok) / Math.max(1, r.fencedTok + r.otherTok + r.htmlTok)), stack: r.hasStack }));
  results[id] = { ...R, perYear, extrapolation: { stratified: point, naive, ci90: ci }, top };
}
writeFileSync(outPath, JSON.stringify(results, null, 1));
console.log('ok');
