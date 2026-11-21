// Brute-force top-k over a date-sorted prefix: Float32 cosine and Int8 scalar-quantized.
import { openSync, readSync, closeSync, readFileSync } from 'node:fs';
const [dataDir, nArg] = process.argv.slice(2);
const N = Number(nArg), D = 384, K = 50, WARMUP = 5;
const mb = (x) => Math.round(x / 1048576);
const rss0 = process.memoryUsage().rss;
function readPrefix(file, bytes, ctor) {
  const arr = new ctor(bytes / ctor.BYTES_PER_ELEMENT);
  const fd = openSync(file, 'r'); let off = 0;
  const u8 = new Uint8Array(arr.buffer);
  while (off < bytes) off += readSync(fd, u8, off, Math.min(bytes - off, 1 << 30), off);
  closeSync(fd); return arr;
}
let t = performance.now();
const vecs = readPrefix(`${dataDir}/vectors.f32`, N * D * 4, Float32Array);
const created = readPrefix(`${dataDir}/created_at.f64`, N * 8, Float64Array);
const loadMs = performance.now() - t;
const rssF32 = process.memoryUsage().rss;
// Scalar quantization with one global symmetric scale.
let maxAbs = 0; for (let i = 0; i < vecs.length; i++) { const a = Math.abs(vecs[i]); if (a > maxAbs) maxAbs = a; }
const scale = 127 / maxAbs;
t = performance.now();
const q8 = new Int8Array(vecs.length);
for (let i = 0; i < vecs.length; i++) q8[i] = Math.round(vecs[i] * scale);
const quantMs = performance.now() - t;
const rssBoth = process.memoryUsage().rss;

function visibleCount(cutoff) { // first index with created_at >= cutoff (sorted ascending)
  let lo = 0, hi = N; while (lo < hi) { const m = (lo + hi) >>> 1; if (created[m] < cutoff) lo = m + 1; else hi = m; } return lo;
}
function makeHeap() { return { s: new Float64Array(K), i: new Int32Array(K), n: 0 }; }
function push(h, score, idx) {
  const s = h.s, ix = h.i;
  if (h.n < K) { let c = h.n++; while (c > 0) { const p = (c - 1) >> 1; if (s[p] <= score) break; s[c] = s[p]; ix[c] = ix[p]; c = p; } s[c] = score; ix[c] = idx; return; }
  if (score <= s[0]) return;
  let c = 0; for (;;) { const l = 2 * c + 1; if (l >= K) break; const r = l + 1; const m = (r < K && s[r] < s[l]) ? r : l; if (s[m] >= score) break; s[c] = s[m]; ix[c] = ix[m]; c = m; }
  s[c] = score; ix[c] = idx;
}
function sorted(h) { const o = []; for (let j = 0; j < h.n; j++) o.push([h.s[j], h.i[j]]); return o.sort((a, b) => b[0] - a[0]).map((x) => x[1]); }
function searchF32(q, cutoff) {
  const M = visibleCount(cutoff), h = makeHeap();
  for (let r = 0, o = 0; r < M; r++, o += D) {
    let s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (let j = 0; j < D; j += 4) { s0 += q[j] * vecs[o + j]; s1 += q[j + 1] * vecs[o + j + 1]; s2 += q[j + 2] * vecs[o + j + 2]; s3 += q[j + 3] * vecs[o + j + 3]; }
    push(h, s0 + s1 + s2 + s3, r);
  }
  return sorted(h);
}
function searchI8(qi, cutoff) {
  const M = visibleCount(cutoff), h = makeHeap();
  for (let r = 0, o = 0; r < M; r++, o += D) {
    let s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (let j = 0; j < D; j += 4) { s0 = (s0 + qi[j] * q8[o + j]) | 0; s1 = (s1 + qi[j + 1] * q8[o + j + 1]) | 0; s2 = (s2 + qi[j + 2] * q8[o + j + 2]) | 0; s3 = (s3 + qi[j + 3] * q8[o + j + 3]) | 0; }
    push(h, (s0 + s1 + s2 + s3) | 0, r);
  }
  return sorted(h);
}
const median = (a) => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const configs = JSON.parse(readFileSync(`${dataDir}/queries.json`, 'utf8')).filter((c) => c.N === N);
const out = { node: process.version, N, loadMs: Math.round(loadMs), rssBaselineMB: mb(rss0), rssAfterF32MB: mb(rssF32), rssAfterF32andI8MB: mb(rssBoth), quantMs: Math.round(quantMs), results: [] };
for (const c of configs) {
  const qs = c.queries.map((x) => Float32Array.from(x.vec));
  const qis = c.queries.map((x) => Int8Array.from(x.vec, (v) => Math.max(-127, Math.min(127, Math.round(v * scale)))));
  for (let w = 0; w < WARMUP; w++) { searchF32(qs[w], c.cutoff); searchI8(qis[w], c.cutoff); }
  const tf = [], ti = []; let hitF = 0, hitI = 0, recall = 0; const f32Tops = [];
  for (let k = 0; k < qs.length; k++) {
    let t0 = performance.now(); const rf = searchF32(qs[k], c.cutoff); tf.push(performance.now() - t0);
    t0 = performance.now(); const ri = searchI8(qis[k], c.cutoff); ti.push(performance.now() - t0);
    if (rf[0] === c.queries[k].target) hitF++; if (ri[0] === c.queries[k].target) hitI++;
    const set = new Set(rf); recall += ri.filter((x) => set.has(x)).length / K; f32Tops.push(rf);
    if (Math.max(...rf) >= c.visible) throw new Error('date filter violated');
  }
  out.results.push({ frac: c.frac, visible: c.visible, queries: qs.length, f32MedianMs: +median(tf).toFixed(2), i8MedianMs: +median(ti).toFixed(2), f32Top1Hit: hitF / qs.length, i8Top1Hit: hitI / qs.length, i8RecallAt50VsF32: +(recall / qs.length).toFixed(3) });
}
console.log(JSON.stringify(out, null, 1));
