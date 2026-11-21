// sqlite-vec vec0 KNN with a created_at metadata filter, through node:sqlite + loadExtension.
const { openSync, readSync, closeSync, readFileSync, statSync, rmSync, existsSync } = require('node:fs');
const { createRequire } = require('node:module');
const sqlite = require('node:sqlite');
const [dataDir, nArg, dbPath, projDir] = process.argv.slice(2);
const N = Number(nArg), D = 384, K = 50, WARMUP = 5;
const Db = sqlite.Database ?? sqlite.DatabaseSync;
const vecPath = createRequire(projDir + '/package.json')('sqlite-vec').getLoadablePath();
function readPrefix(file, bytes, ctor) {
  const arr = new ctor(bytes / ctor.BYTES_PER_ELEMENT); const fd = openSync(file, 'r'); let off = 0; const u8 = new Uint8Array(arr.buffer);
  while (off < bytes) off += readSync(fd, u8, off, Math.min(bytes - off, 1 << 30), off); closeSync(fd); return arr;
}
const vecs = readPrefix(`${dataDir}/vectors.f32`, N * D * 4, Float32Array);
const created = readPrefix(`${dataDir}/created_at.f64`, N * 8, Float64Array);
for (const f of [dbPath, dbPath + '-journal', dbPath + '-wal']) if (existsSync(f)) rmSync(f);
let db = new Db(dbPath, { allowExtension: true }); db.loadExtension(vecPath);
const vecVersion = db.prepare('select vec_version() v').get().v, sqliteVersion = db.prepare('select sqlite_version() v').get().v;
db.exec('create virtual table pieces using vec0(embedding float[384] distance_metric=cosine, created_at integer)');
const ins = db.prepare('insert into pieces(rowid, embedding, created_at) values (?, ?, ?)');
let t = performance.now();
const BATCH = 10_000;
for (let i = 0; i < N; i += BATCH) {
  db.exec('begin');
  for (let r = i; r < Math.min(N, i + BATCH); r++) ins.run(BigInt(r + 1), new Uint8Array(vecs.buffer, r * D * 4, D * 4), BigInt(created[r]));
  db.exec('commit');
}
const buildMs = performance.now() - t;
db.close();
const fileBytes = statSync(dbPath).size;
t = performance.now();
db = new Db(dbPath, { allowExtension: true }); db.loadExtension(vecPath);
const openMs = performance.now() - t;
const knn = db.prepare('select rowid, distance from pieces where embedding match ? and k = 50 and created_at < ?');
function bruteTop(q, visible) { const sc = []; for (let r = 0; r < visible; r++) { let s = 0; for (let j = 0; j < D; j++) s += q[j] * vecs[r * D + j]; sc.push([s, r]); } sc.sort((a, b) => b[0] - a[0]); return sc.slice(0, K).map((x) => x[1]); }
const median = (a) => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const configs = JSON.parse(readFileSync(`${dataDir}/queries.json`, 'utf8')).filter((c) => c.N === N);
const out = { node: process.version, sqliteVersion, vecVersion, N, buildMs: Math.round(buildMs), fileMB: +(fileBytes / 1048576).toFixed(1), openMs: +openMs.toFixed(1), results: [] };
for (const c of configs) {
  const qs = c.queries.map((x) => Float32Array.from(x.vec));
  const cutoff = BigInt(c.cutoff);
  const run = (q) => knn.all(new Uint8Array(q.buffer), cutoff);
  for (let w = 0; w < WARMUP; w++) run(qs[w]);
  const ts = []; let hit = 0, overlap = 0;
  for (let k = 0; k < qs.length; k++) {
    const t0 = performance.now(); const rows = run(qs[k]); ts.push(performance.now() - t0);
    const ids = rows.map((r) => Number(r.rowid) - 1);
    if (ids.length !== K) throw new Error('got ' + ids.length);
    if (Math.max(...ids) >= c.visible) throw new Error('date filter violated');
    if (ids[0] === c.queries[k].target) hit++;
    if (k < 10) { const set = new Set(bruteTop(qs[k], c.visible)); overlap += ids.filter((x) => set.has(x)).length / K; }
  }
  out.results.push({ frac: c.frac, visible: c.visible, queries: qs.length, medianMs: +median(ts).toFixed(2), top1Hit: hit / qs.length, overlapWithExactTop50: +(overlap / 10).toFixed(3) });
}
out.rssAfterQueriesMB = Math.round(process.memoryUsage().rss / 1048576);
console.log(JSON.stringify(out));
