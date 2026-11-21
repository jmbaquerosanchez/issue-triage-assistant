import { createRequire } from 'node:module';
const req = createRequire(process.argv[2] + '/package.json');
const t0 = performance.now();
const { pipeline, env } = await import(req.resolve('@huggingface/transformers'));
env.cacheDir = process.argv[3];
const ext = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', { device: 'cpu', dtype: 'q8' });
const out = await ext(['hello world', 'otra frase'], { pooling: 'mean', normalize: true });
console.log('dims', out.dims, 'ms', Math.round(performance.now() - t0));
