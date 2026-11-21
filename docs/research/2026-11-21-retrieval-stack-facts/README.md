> Snapshot of 2026-11-21 for [Retrieval stack: store, embedding model and reranker](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/12). Not updated: later research supersedes it.

# Facts for the retrieval stack: corpus size, free tiers, packages and vector scan

These facts were gathered on **2026-11-21** while resolving ticket #12 of the phase-1 map (#2). They add to the reports [Embedding and reranking models usable from TypeScript](../2026-11-20-embedding-reranking-models.md) and [Stores with hybrid search for a local TypeScript tool](../2026-11-20-hybrid-search-stores.md), and supersede neither. This report holds facts and measurements only. The decisions are in the ticket's resolution comment.

Statements marked **observed** come from local runs, on Linux x64 under WSL2 with an Intel Core i7-1255U, the same laptop as the earlier reports. Everything else cites its source.

## Summary

- **The target repository's corpus is about 50M tokens capped at 512, and about 75M uncapped.** godotengine/godot has 64,503 issues and about 285k comments. Titles plus bodies come to about 20M tokens capped at 512 (32M uncapped). Human comments come to about 30M capped (43M uncapped). godot issues are shorter than the four-repository sample of the earlier report: **17% exceed 512 tokens**, against 55% there, and the median is 285 tokens (§ 1).
- **Embedding that corpus locally is a one-off job of hours** (derived estimate, § 1.4):
  - granite-embedding-small-english-r2 (q8): about 2.6 h for issues only, about 6.5 h with comments;
  - bge-small-en-v1.5 (q8): about 2 h for issues only, about 4.5 h with comments.
- **Voyage's free trial is the only zero-cost route to a proprietary embedding model** (§ 2):
  - 200M tokens per model, given once, with no card;
  - but limited to **10K tokens per minute** without a card, which is about 33 h for 20M tokens and 3.5 days for 50M;
  - with a card the work takes minutes and stays free, but Atlas offers billing alerts, not a hard cap;
  - GitHub Models, which offered free OpenAI embeddings, was retired on 2026-07-30.
- **Every store and model package checked ships prebuilt binaries for Linux x64 and arm64, macOS arm64 and Windows x64** (§ 3). `node:sqlite` is a release candidate with no experimental warning since Node 24.15.0, and it loads sqlite-vec. `onnxruntime-node`'s install script only fetches the CUDA provider on Linux x64, so blocking it under pnpm leaves CPU inference working.
- **A plain TypeScript scan over date-sorted vectors beats sqlite-vec, most of all under early cutoffs** (observed, § 4). At 350k pieces of 384 dimensions it takes 141 ms with everything visible and 7 ms with 5% visible, against 214 ms and 105 ms for sqlite-vec. The price is memory: about 520 MB of RSS for 350k float32 vectors.

## 1. Token counts of godotengine/godot

### 1.1 Sample

- **Size:** 23 issues per creation year, 2014–2026, for 299 issues and their 1,349 comments.
- **Selection:** within each year, random issue numbers from that year's number range. PRs were discarded: 219 of the 520 numbers tried were PRs, and 2 no longer existed.
- **Fetching:** title, body and every comment, over GraphQL. A comment counts as a bot's when the author type is `Bot` or the login ends in `[bot]`. No login was stored.
- **Tokenizers:** two, through Transformers.js 3.8.1, with no special tokens, on the raw markdown, with title and body joined by a blank line:
  - `Xenova/bge-small-en-v1.5` (BERT WordPiece);
  - `onnx-community/granite-embedding-small-english-r2-ONNX` (ModernBERT).
- **Weighting:** every figure is weighted by the real number of issues per year, from the search API's `total_count` (`scripts/godot-tokens/out/years.csv`). Those counts add up to 64,497, scaled to 64,503. Without the weights, the means come out about 10% lower, because equal numbers per year oversample the short issues of 2014–2017.

### 1.2 Issue title + body

| | bge-small (WordPiece) | granite-small-r2 (ModernBERT) |
|---|---|---|
| Mean / median | 494 / 285 | 485 / 279 |
| p90 / p99 | 691 / 2,308 | 680 / 1,997 |
| Share over 256 / 512 | 56.3% / 17.2% | 59.2% / 17.6% |
| Share over 1,024 / 2,048 / 8,192 | 5.8% / 1.3% / 0.3% | 6.1% / 0.8% / 0.3% |
| Mean capped at 256 / 512 / 1,024 / 2,048 | 222 / 311 / 361 / 395 | 223 / 311 / 360 / 391 |

The share over 8,192 tokens is a single issue.

| Year | Issues | Mean (bge) | Median | Mean capped at 512 | Share in code blocks |
|---|---|---|---|---|---|
| 2014 | 756 | 103 | 72 | 103 | 6% |
| 2015 | 1,457 | 124 | 99 | 124 | 17% |
| 2016 | 2,717 | 208 | 188 | 208 | 15% |
| 2017 | 3,858 | 254 | 172 | 232 | 21% |
| 2018 | 5,864 | 252 | 248 | 252 | 6% |
| 2019 | 5,968 | 287 | 233 | 258 | 16% |
| 2020 | 5,118 | 1,705 (429 without one outlier) | 354 | 357 | 84% |
| 2021 | 5,350 | 546 | 398 | 369 | 39% |
| 2022 | 7,121 | 479 | 332 | 346 | 28% |
| 2023 | 8,965 | 442 | 336 | 342 | 29% |
| 2024 | 6,842 | 509 | 376 | 357 | 25% |
| 2025 | 6,065 | 311 | 263 | 303 | 4% |
| 2026 (to Nov 21) | 4,416 | 559 | 437 | 387 | 10% |

With 23 issues per year, each year's mean is noisy (±30–50%).

### 1.3 Comments

- **Volume:** 4.42 comments per issue on average (median 3).
- **Bots:** 0.1% of comments.

| Tokens per human comment | bge-small | granite-small-r2 |
|---|---|---|
| Mean / median | 152 / 63 | 147 / 59 |
| p90 / p99 | 264 / 1,116 | 251 / 1,131 |
| Share over 256 / 512 | 10.1% / 3.2% | 9.6% / 3.6% |
| Mean capped at 256 / 512 | 90 / 104 | 88 / 103 |

### 1.4 Extrapolation to the whole repository

The sample gives an estimated **285,162 comments** (90% interval 0.26–0.33M), which matches the ~285k measured on the same day by #9. The intervals come from 2,000 resamples within each year, with the bge-small tokenizer.

| Total tokens | bge-small (90% interval) | granite-small-r2 |
|---|---|---|
| Issues, uncapped | 31.9M (23.6–41.0M) | 31.3M |
| Issues capped at 512 | 20.1M (19.2–20.8M) | 20.1M |
| Issues capped at 2,048 | 25.5M (23.2–27.8M) | 25.2M |
| Human comments, uncapped | 43.4M (30.6–59.5M) | 41.9M |
| Human comments capped at 512 | 29.7M (25.3–36.3M) | 29.2M |
| **Everything uncapped / everything capped at 512** | **75.3M / 49.8M** | **73.2M / 49.3M** |

- **A few huge items drive the uncapped totals.** One 2020 issue holds 29.8k tokens, all of it a log inside a code block. Without it, issues come to 25.3M tokens (mean 393). Without the one 31k-token comment, human comments come to 35.3M. The capped totals barely move, so they deserve more trust (about ±5%) than the uncapped ones.
- **Capping is not chunking.** bge-small's limit is 512 tokens, so any cap above it means chunking, and chunked totals come close to the uncapped ones. Each embedded chunk also adds 2 special tokens, which were not counted.

**Derived embedding time.** This is not a measured run. It divides the totals above by the CPU throughput that the earlier report measured on the same laptop, at a cap of 512, where the mean capped issue had 405 tokens:

- bge-small q8 ran at 6.5–8.4 issues per second, about 2.6–3.4k tokens per second: about **2 h** for issues capped at 512 and about **4.5 h** for everything capped at 512;
- granite-small-r2 q8 ran at 5.3 issues per second, about 2.1k tokens per second: about **2.6 h** and about **6.5 h**.

Shorter inputs such as comments probably run somewhat faster per token. The earlier report measured ±25% run-to-run noise, and fp32 roughly halves the throughput.

### 1.5 What makes issues long

- **Code blocks (fenced with three backticks):** they hold 39% of issue-body tokens, or 23% without the outlier. 24% of issues have at least one. Comments look the same: 39% of tokens in code blocks, 24.5% without their outlier. The five longest comments are 91–100% code block: logs and code. The shares were approximated by tokenizing the code blocks and the rest separately.
- **Templates:** the old Markdown template (`**Godot version:**` and so on) appears in 44–87% of each year's sample from 2016 to 2021. GitHub issue forms (`### Tested versions` and so on) appear in 100% from 2022 on. The headings cost only tens of tokens. The length comes from the system information, logs and reproduction code the templates ask for. Instructions left in HTML comments are 1.5% of tokens overall, and 9–10% in 2018–2019.
- **Stack traces and crash logs:** about 4% of issues, by a rough regular expression.

## 2. Free tiers of hosted embedding and reranking APIs

The goal was to embed about 60M tokens once, at zero cost or at a small, hard-capped one-off cost. All pages were read on 2026-11-21. *Inferred* marks what follows from the pages without being stated in them.

| Provider | Free allowance | Card needed | Free-tier throughput | 60M tokens on the free tier | Spend control | Data use on the free tier |
|---|---|---|---|---|---|---|
| **Voyage (MongoDB Atlas)** | 200M tokens per model, given once ("do not refresh"), on voyage-4-large, voyage-4, voyage-4-lite, voyage-code-4, rerank-3 and rerank-3-lite. Older models get none on Atlas, although the old docs.voyageai.com pricing page says otherwise. | No | Without a card: **3 RPM, 10K TPM**. With a card (Tier 1): 2,000 RPM and 3M–16M TPM, and the free tokens still apply. Up to 1,000 texts and 120K–1M tokens per request. | About 100 h (~4 days); 150M take about 10 days. With a card, minutes, and still free. | Billed after use (monthly invoice). Billing alerts only; no hard cap found. | May be used to train Voyage models. Opting out "requires a valid payment method on file". |
| **OpenAI** | None documented. "Free" is a rate-limit tier only; usage is paid from prepaid credits. | Yes, at least $5 of credits | Free tier: 100 RPM, 2,000 RPD, 40K TPM. Build tier: 5,000 RPM, 1M TPM. | Not possible for free. Paid: about 1 h, $1.20 (text-embedding-3-small) or $7.80 (3-large). | Prepaid credits. Auto-reload is **on by default**. Organization and project hard monthly limits exist ("can slightly exceed"). | Not used for training by default (since 2023-03-01). |
| **Gemini API** | gemini-embedding-001 and gemini-embedding-2 are "Free of charge" on the free tier, which does not run out (rate-limited only). | No | **Not published**; the docs point to AI Studio. A forum user (December 2025) reports 100 RPM, 30K TPM and 1K RPD for 001. | About 33 h if TPM binds; up to about 2 months if each text counts against RPD *(inferred)*. | Paid: prepay at least $5; keys stop at a $0 balance, with about 10 minutes of possible overage. | Used "to improve… products", and human reviewers may read it. In the EEA, Switzerland and the UK the paid-tier data terms apply. |
| **Cohere** | Trial key: free, **1,000 calls/month** across all endpoints | No | Embed: 2,000 inputs/min, 96 texts per call. Rerank: 10 requests/min. | About 672 calls, so it fits in one month for titles + bodies *(inferred)*. Not with comments. | Production keys are billed monthly, or at $250 outstanding. No cap found. | Trial input and output may be used for R&D (de-identified). Trial keys "are not permitted to be used for production or commercial purposes". |
| **GitHub Models** | **Retired on 2026-07-30** | – | – | – | – | – |
| **Jina (now Elastic)** | 10M tokens per new key; keys do not expire | Probably not *(inferred)* | Free key: 100 RPM, 100K TPM | Only about 1/6 of 60M is free | Prepaid token packs; auto top-up is opt-in | "Never" used for training |
| **Mistral** | None: Free mode "doesn't include API access" | Billing must be activated | Shown only in the admin panel | Not possible | Prepaid credits and an organization monthly spending limit | Not checked |
| **Cloudflare Workers AI** | **10,000 neurons/day**, resetting daily, on the Free and Paid plans | Not stated; probably not *(inferred)* | 3,000 RPM for text embeddings | About 1 day (embeddinggemma-2) to about 36 days (bge-base), depending on the model | Free plan: requests fail past the allocation, a hard stop | No training, zero retention |
| **Hugging Face Inference Providers** | None for free users; PRO accounts get $2/month | Credits must be bought | – | Not possible | Prepaid credits | Not checked |

What follows from the table:

- **Voyage without a card** is the only zero-cost row for a proprietary model. At 10K TPM, any single request over 10K tokens probably cannot go through *(inferred)*.
- **Cloudflare** is hard-capped at $0 and does not train on the data, but every model it hosts has open weights, which run locally anyway.
- **A small cost with a hard cap** is possible through OpenAI's prepaid credits (with auto-reload turned off and a project limit) or Gemini's prepaid balance. Voyage with a card is free but has no hard cap.
- **A hosted reranker** does not fit Voyage's free trial without a card: one request with 20 candidates of about 400 tokens and a 400-token query is already about 16K billed tokens, over the 10K TPM limit *(inferred)*. Cohere's trial limits rule it out too.

Not determined:

- Gemini's free-tier limits for embedding models, and whether each item in a batch call counts as a request.
- How Voyage handles a request larger than the per-minute token limit, and whether Atlas has any hard spending cap.
- Whether OpenAI gives new accounts any free credits.
- Jina's per-token price, and whether a key needs signup.
- Which of Mistral's free-API statements is current.
- Whether Cloudflare Workers Free needs a card, and whether its spending limit covers Workers AI.
- Cohere's embed-v5 price, and whether trial data can be opted out.
- Terms on storing the returned vectors: only Gemini ("won't claim ownership") and Cloudflare (embeddings are "Customer Content") were checked, and neither restricts it.

Sources:

- **Voyage:** [API overview](https://www.mongodb.com/docs/voyageai/api-reference/overview/), [billing](https://www.mongodb.com/docs/voyageai/management/billing/), [rate limits](https://www.mongodb.com/docs/voyageai/management/rate-limits/), [automated embedding billing](https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/billing/), [text embedding models](https://www.mongodb.com/docs/voyageai/models/text-embeddings/), [Atlas organization settings](https://www.mongodb.com/docs/atlas/tutorial/manage-organization-settings/), [Atlas billing](https://www.mongodb.com/docs/atlas/billing/), [old pricing page](https://docs.voyageai.com/docs/pricing).
- **OpenAI:** [rate limits](https://developers.openai.com/api/docs/guides/rate-limits), [spend limits](https://developers.openai.com/api/docs/guides/spend-limits), [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small), [your data](https://developers.openai.com/api/docs/guides/your-data), [help article 8264644](https://help.openai.com/en/articles/8264644).
- **Gemini:** [rate limits](https://aistudio.google.com/docs/rate-limits), [pricing](https://aistudio.google.com/docs/pricing), [billing](https://aistudio.google.com/docs/billing), [terms](https://aistudio.google.com/docs/terms), [gemini-embedding-001](https://aistudio.google.com/docs/models/gemini-embedding-001), [forum thread 112553](https://discuss.ai.google.dev/t/112553).
- **Cohere:** [rate limits](https://docs.cohere.com/docs/rate-limits), [embed](https://docs.cohere.com/reference/embed), [rerank](https://docs.cohere.com/reference/rerank), [Cohere Embed](https://docs.cohere.com/docs/cohere-embed), [pricing](https://cohere.com/pricing).
- **GitHub Models:** [docs](https://docs.github.com/en/github-models), [retirement changelog](https://github.blog/changelog/2026-07-30-github-models-is-now-retired/).
- **Jina:** [embeddings](https://jina.ai/embeddings/), [reranker](https://jina.ai/reranker/).
- **Mistral:** [usage limits](https://docs.mistral.ai/admin/billing-usage/usage-limits), [help article 698531](https://help.mistral.ai/en/articles/698531).
- **Cloudflare:** [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [limits](https://developers.cloudflare.com/workers-ai/platform/limits/), [data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/), [spend management](https://developers.cloudflare.com/workers/platform/spend-management/).
- **Hugging Face:** [Inference Providers pricing](https://huggingface.co/docs/inference-providers/pricing).

## 3. Packages, platform binaries and install scripts

The four promised platforms are Linux x64, Linux arm64, macOS arm64 and native Windows x64, under Node ≥ 24 with pnpm. pnpm blocks dependency install scripts unless each package is allowlisted. Package facts come from the npm registry (`npm view <package> --json`) and the published tarballs. Loading was observed on Linux x64 only.

- **`node:sqlite`.**
  - The latest releases are Node 24.22.3 (LTS "Krypton") and 26.13.1 (LTS "Lithium") ([index.json](https://nodejs.org/dist/index.json)).
  - Both lines' docs say "Stability: 1.2 - Release candidate" ([v24](https://nodejs.org/docs/latest-v24.x/api/sqlite.html), [v26](https://nodejs.org/docs/latest-v26.x/api/sqlite.html)). The change, in [nodejs/node#61262](https://github.com/nodejs/node/pull/61262), landed in v24.15.0 and v25.7.0, and it also removed the experimental warning. **Observed:** importing it prints nothing on 24.16.0, 24.22.3 and 26.13.1. Node 24 releases before 24.15.0 still print the warning.
  - `allowExtension` and `loadExtension()` are documented in both lines. **Observed:** they load sqlite-vec.
  - **Observed:** FTS5 is compiled in. The bundled SQLite is 3.53.0 on Node 24.16.0 and 3.54.1 on 24.22.3 and 26.13.1.
  - Node 26.11.0 renamed `DatabaseSync` to `Database`, keeping the old name as an alias deprecated in the docs only (DEP0210).
- **sqlite-vec.**
  - The latest stable is 0.1.9 (2026-03-31) and the latest alpha 0.1.10-alpha.4 (2026-05-18).
  - Platform packages exist for linux-x64, linux-arm64, darwin-arm64, darwin-x64 and windows-x64; there is none for Windows arm64 or musl. They have no install scripts: the tarballs hold only the binary, `package.json` and a README.
  - The [repository](https://github.com/asg017/sqlite-vec) had its last commit on 2026-05-18, about six months before this snapshot.
- **better-sqlite3 13.2.0** (2026-11-14).
  - No `install` or `postinstall` script, and `"gypfile": false`. Since 13.0.0 it uses N-API and ships its binaries inside the npm tarball, for linux x64 and arm64 (glibc and musl), darwin x64 and arm64, and win32 x64 and arm64. They are not tied to a Node ABI.
  - **Observed:** pnpm 11.5 still lists it under "Ignored build scripts", because the package contains `binding.gyp`. Left unapproved, the prebuilt binary works. Approved, pnpm runs `node-gyp rebuild`, which on Linux finds the prebuilt binary and compiles nothing. This was not tested on Windows without a toolchain.
- **libSQL.** `@libsql/client` 0.18.0 depends on `libsql` 0.5.29, with native packages for linux-x64-gnu, linux-arm64-gnu, darwin-arm64 and win32-x64-msvc, among others. No install scripts. **Observed:** it embeds SQLite 3.45.1, and FTS5 works.
- **`@lancedb/lancedb` 0.41.0.**
  - Platform packages exist for linux x64 and arm64 (glibc), darwin-arm64 and win32-x64-msvc, among others; darwin-x64 stopped at 0.22.x. No install scripts.
  - Its `optionalDependencies` include `@huggingface/transformers` 3.0.2 and `openai` 4.29.2. **Observed:** pnpm then flags the install scripts of onnxruntime-node 1.19.2, sharp 0.33.5 and protobufjs 7.6.6.
- **`onnxruntime-node` 1.30.0**, the version Transformers.js 4.3.2 pins; the latest is 1.31.1.
  - The CPU binaries are inside the tarball, for linux x64 and arm64, win32 x64 and arm64, and darwin arm64: 301 MB unpacked. There is no darwin-x64 build.
  - `postinstall` (`node ./script/install`) only downloads what `install-metadata.js` lists. By default that is the CUDA 12 provider on linux x64, fetched from NuGet; on the other platforms it downloads nothing. `ONNXRUNTIME_NODE_INSTALL=skip` turns it off.
  - **Observed:** with the script blocked by pnpm, CPU feature extraction with `Xenova/all-MiniLM-L6-v2` (q8) works. Only the CUDA provider is lost.
- **`@huggingface/transformers` 4.3.2** (2026-10-27).
  - Its dependencies are sharp ^0.35.4, onnxruntime-node 1.30.0, onnxruntime-web 1.31.0-dev, `@huggingface/jinja` and `@huggingface/tokenizers`.
  - sharp 0.35 has no install script, and its native code comes in `@img/sharp-*` optional packages for all four platforms. **Observed:** the Node build requires sharp at the top level, so importing Transformers.js without sharp's binary fails ("Could not load the 'sharp' module"), even for text models.
  - **Observed:** the install scripts left in the tree are those of onnxruntime-node and of protobufjs 7.6.6, which onnxruntime-web pulls in. pnpm 11.5 exits with `ERR_PNPM_IGNORED_BUILDS` while they are unreviewed, though it installs the packages. With `allowBuilds: {onnxruntime-node: false, protobufjs: false}` in `pnpm-workspace.yaml` it exits 0.

Not determined: how any of this behaves on macOS, Windows or arm64 beyond what the registry metadata and tarball contents show.

## 4. Exact vector scan at 65k and 350k pieces (observed)

**Setup:**

- **Software:** Node 24.16.0, on the i7-1255U under WSL2 with about 2.6 GB of RAM free.
- **Data:** deterministic random unit vectors of 384 dimensions, with an ascending `created_at` per piece. Each query is a stored vector plus noise.
- **Measure:** the median of 30 queries after 5 warm-ups, top k = 50, with cutoffs leaving 100%, 50% and 5% of the pieces visible.
- **Three methods:**
  - **JS Float32:** a binary search on `created_at` finds the cutoff, then the code scans that prefix of one `Float32Array` (normalized vectors, dot product, loops unrolled by 4) and keeps a min-heap.
  - **JS Int8:** the same over scalar-quantized vectors with one global scale, accumulated in integers.
  - **sqlite-vec 0.1.9:** a `vec0` table with `distance_metric=cosine` and `created_at` as a metadata column, queried with `WHERE embedding MATCH ? AND k = 50 AND created_at < ?` through `node:sqlite` and `loadExtension`.

| Pieces | Visible | JS Float32 (ms) | JS Int8 (ms) | sqlite-vec (ms) |
|---|---|---|---|---|
| 65k | 100% | 21.1 | 18.2 | 34.6 |
| 65k | 50% | 10.9 | 9.2 | 26.7 |
| 65k | 5% | 1.07 | 0.94 | 18.5 |
| 350k | 100% | 141 | 124 | 214 |
| 350k | 50% | 68.5 | 60.7 | 165 |
| 350k | 5% | 6.8 | 5.9 | 105 |

- **Variance:** 10–30% between runs. A repeat at 350k with everything visible gave 130 ms (Float32) and 114 ms (Int8). sqlite-vec gave 231 ms on Node 24 and 221 ms on Node 26.13.1.
- **Memory:** RSS was 46 MB at baseline and 562–566 MB after loading the 350k Float32Array, which took 0.3–0.5 s from a raw file. Adding the Int8 copy took it to 699 MB.
- **Build:** the sqlite-vec table took 5.3–5.7 s for 350k rows, in transactions of 10k rows, and the file was 549.7 MB. At 65k it took 1.0 s and the file was 102.8 MB.
- **Correctness:** every method put the target first in every query. sqlite-vec's top 50 matched the exact top 50. The Int8 top 50 overlapped the Float32 top 50 by 0.97–0.98. No result broke the date filter.
- **Main finding:** in sqlite-vec the date filter cuts the cost far less than in proportion: with 5% visible it still costs about half the full query. The scan of a date-sorted prefix shrinks linearly. Why vec0 does not prune in proportion was not investigated.

Random vectors are not real embeddings. The overlap between Int8 and Float32 on real embeddings was not measured.

## Method and reproducibility

The scripts are in [`scripts/`](scripts/). Each takes the directory where its npm packages are installed as an argument, so they run from outside that directory.

- **`scripts/godot-tokens/`**, for § 1.
  - `years.sh <out.csv>`: issues per year and each year's issue-number range, through the search API with the `gh` CLI.
  - `sample.mjs <years.csv> <sample.json> [perYear] [seed]`: the stratified sample over GraphQL. The default seed is 20261121.
  - `analyze.mjs` and `sensitivity.mjs`: token statistics, extrapolation, resampling intervals and the outlier sensitivity, with Transformers.js 3.8.1.
  - **Kept:** only the aggregates, in `out/years.csv` and `out/results.json`. The sample itself is not committed: it holds the text of third-party issues and comments, whose redistribution #5 found unclear. `sample.mjs` rebuilds it, although later edits and deletions on GitHub will change it.
- **`scripts/store-checks/`**, for §§ 3 and 4.
  - `gen.mjs <outDir>`: the deterministic vectors (seed 42), dates and query sets. They are about 540 MB and not committed.
  - `bf.mjs <dataDir> <N>`: the TypeScript Float32 and Int8 scan.
  - `sv-bench.cjs <dataDir> <N> <db> <pkgDir>`: the sqlite-vec benchmark.
  - `nodesqlite-vec.cjs`, `load-test.cjs`, `load-others.mjs` and `hf-test.mjs`: the load checks for `node:sqlite` with sqlite-vec, better-sqlite3, libSQL with LanceDB, and Transformers.js.
  - **Results:** in `out/`.
- **Versions:** sqlite-vec 0.1.9, better-sqlite3 13.2.0, `@libsql/client` 0.18.0, `@lancedb/lancedb` 0.41.0, Transformers.js 4.3.2 for the load checks and 3.8.1 for the tokenizers, and pnpm 11.5.
- **§ 2** came from reading the cited pages. No account was created and no API key was used.
