// Generates deterministic test data: 350k random unit vectors (384 dims),
// ascending created_at, and query sets per (N, visible fraction).
import { writeFileSync } from 'node:fs';
const [outDir] = process.argv.slice(2);
const D = 384, NMAX = 350_000, K_QUERIES = 30;
function mulberry32(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const rnd = mulberry32(42);
let spare = null;
function gauss() { if (spare !== null) { const s = spare; spare = null; return s; } let u = 0; while (u === 0) u = rnd(); const v = rnd(); const r = Math.sqrt(-2 * Math.log(u)); spare = r * Math.sin(2 * Math.PI * v); return r * Math.cos(2 * Math.PI * v); }
const vecs = new Float32Array(NMAX * D);
for (let i = 0; i < NMAX; i++) {
  let n = 0; const o = i * D;
  for (let j = 0; j < D; j++) { const g = gauss(); vecs[o + j] = g; n += g * g; }
  n = 1 / Math.sqrt(n);
  for (let j = 0; j < D; j++) vecs[o + j] *= n;
}
writeFileSync(`${outDir}/vectors.f32`, new Uint8Array(vecs.buffer));
// created_at: ascending unix seconds, one piece per ~37 s with jitter
const created = new Float64Array(NMAX); let t = 1_600_000_000;
for (let i = 0; i < NMAX; i++) { t += 1 + Math.floor(rnd() * 73); created[i] = t; }
writeFileSync(`${outDir}/created_at.f64`, new Uint8Array(created.buffer));
// Queries: stored vector + gaussian noise (per-component sigma = 0.5/sqrt(D)), normalized.
const sigma = 0.5 / Math.sqrt(D);
const configs = [];
for (const N of [65_000, 350_000]) for (const frac of [1, 0.5, 0.05]) {
  const visible = Math.round(N * frac);
  const cutoff = visible === N ? created[N - 1] + 1 : created[visible]; // created_at < cutoff leaves exactly `visible`
  const queries = [];
  for (let q = 0; q < K_QUERIES; q++) {
    const target = Math.floor(rnd() * visible);
    const v = new Array(D); let n = 0;
    for (let j = 0; j < D; j++) { const x = vecs[target * D + j] + sigma * gauss(); v[j] = x; n += x * x; }
    n = 1 / Math.sqrt(n);
    queries.push({ target, vec: v.map((x) => x * n) });
  }
  configs.push({ N, frac, visible, cutoff, queries });
}
writeFileSync(`${outDir}/queries.json`, JSON.stringify(configs));
console.log('done');
