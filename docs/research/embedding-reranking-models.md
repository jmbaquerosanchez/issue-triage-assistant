# Embedding and reranking models usable from TypeScript

Research for ticket #7 of the phase-1 map (#2). Sources were read on **2026-11-20**, and every price is as of that date. This note gathers options and trade-offs. It does not choose: the choice is made in #12.

The question has three parts: local models that run from TypeScript, hosted embedding and reranking APIs (including whether their results can be cached so the demo and CI run without a key), and whether a cross-encoder reranker can run locally from TypeScript.

## Summary

- **Local models run from TypeScript.** Transformers.js 4.3.2 (`@huggingface/transformers` on npm) runs ONNX builds of every encoder listed below in Node, on top of `onnxruntime-node`, which ships prebuilt CPU binaries for Linux, macOS and Windows on x64 and arm64. Public, non-gated Hugging Face repositories download without a token. Embedding models and cross-encoder rerankers both ran in this research (§ 5, § 6).
- **CPU time is the main cost of a local model.** On a 2022 laptop CPU (Intel i7-1255U), embedding **50,000 issues** cut at 512 tokens would take about **1.7–2.6 hours** with the 384-dimension models (bge-small-en-v1.5, granite-embedding-small-english-r2, 8-bit), **5–12 hours** with 110–300M models, **10–14 hours** with EmbeddingGemma, and **about 34 hours** with Qwen3-Embedding-0.6B. Cutting at 256 tokens roughly halves those times, and all-MiniLM-L6-v2 at 256 tokens would take **about 25 minutes**. These are estimates extrapolated from measured samples of 32–256 issues. Embedding one new issue at query time takes well under a second with the small models.
- **Issues are long.** In a sample of 800 issues from four large repositories, title plus body averages 914 tokens (median 516, cl100k tokenizer), and **55% exceed 512 BERT tokens**. A 512-token model therefore sees only the start of more than half the issues.
- **No public benchmark measures duplicate GitHub issues.** The closest MTEB tasks are CQADupStack (duplicate questions on StackExchange), StackOverflowDupQuestions, AskUbuntuDupQuestions and SprintDuplicateQuestions. CQADupStack-Unix separates models the most (37–54 nDCG@10). Among local models the top scores are granite-embedding-english-r2 (52.9), Qwen3-Embedding-0.6B (51.5) and granite-embedding-small-english-r2 (51.1). Among hosted models with public scores they are gemini-embedding-001 (53.7) and text-embedding-3-large (50.0). On the other duplicate tasks most models are within a few points of each other. Only the project's own replay eval will measure the real task.
- **Hosted APIs are cheap at this scale.** Title plus body of 50,000 issues is about 46M tokens, which costs **$0.46–$9** depending on the model (§ 7). Voyage gives 200M free tokens on its current models. Reranking 2,000 replayed issues against 50 candidates each is about 80M reranker tokens, or **$1.60–$4** on Voyage.
- **Caching works, but the query side has to be covered too.** A vector depends only on the model and the text, so the corpus can be embedded once and the vectors reused. A demo with no key must still embed the new issue. Three ways exist: embed it with a local model, which means the corpus must use that same local model; replay recorded vectors for a fixed set of demo issues; or use the open-weight voyage-4-nano locally against a corpus embedded by a hosted voyage-4 model, since Voyage documents the two as compatible. That last combination was not tested here.
- **A cross-encoder reranker runs locally from TypeScript.** ms-marco-MiniLM-L-6-v2 (8-bit) scored 14–33 pairs per second on the laptop, so reranking 50 candidates takes about 1.5–3.5 seconds. Larger cross-encoders took 12–56 seconds per 50 candidates.

## 1. The corpus, measured

To size costs and context lengths, 800 issues were sampled through the GitHub search API: 200 each from `microsoft/vscode`, `vercel/next.js`, `rust-lang/rust` and `golang/go`, all created between 2024-01-01 and 2025-06-30, using title plus body without comments. These are not the target repository, which another ticket chooses. Tokens were counted with `js-tiktoken` (`cl100k_base`, the OpenAI tokenizer) and with the WordPiece tokenizer of `bge-small-en-v1.5` (a typical BERT tokenizer).

| Repository | Issues | Mean tokens (cl100k) | Median | p90 | p99 | Over 512 BERT tokens |
|---|---|---|---|---|---|---|
| golang/go | 200 | 525 | 307 | 1,103 | 3,830 | 40% |
| microsoft/vscode | 200 | 757 | 662 | 1,466 | 5,513 | 55% |
| rust-lang/rust | 200 | 1,733 | 585 | 5,009 | 14,545 | 63% |
| vercel/next.js | 200 | 641 | 529 | 986 | 4,289 | 63% |
| **All** | **800** | **914** | **516** | **1,684** | **7,730** | **55%** |

The BERT tokenizer counts about 22% more tokens than cl100k (mean 1,113, median 568). Cut at 512 BERT tokens, the mean issue is 405 tokens.

What follows from this:

- A 512-token model reads the issue template and the opening of the description, but often not the stack trace or logs further down. Models with 2K–32K context read more of each issue, and each issue costs more CPU (§ 5).
- In duplicate search the **query is itself an issue**, so it is long and noisy rather than a short search phrase. This matters for asymmetric models that expect short queries, and for reranker token billing (§ 7).
- The cost estimates below use 50,000 issues × 914 tokens ≈ **45.7M tokens** for title plus body. Comments would multiply this figure; they were not measured.

## 2. Running models from TypeScript

**Transformers.js.** The current release is 4.3.2 (2026-10-28), published on npm as `@huggingface/transformers` and depending on `onnxruntime-node` 1.30.0 ([releases](https://github.com/huggingface/transformers.js/releases), npm metadata). Version 4.0.0 (2026-03-30) reports "a ~4x speedup for BERT-based embedding models" from switching to the MultiHeadAttention operator, and adds WebGPU in Node, Bun and Deno ([releases](https://github.com/huggingface/transformers.js/releases)). 4.3.1 added EmbeddingGemma 2. Typical dtypes are `fp32`, `fp16`, `q8` and `q4` ([docs](https://huggingface.co/docs/transformers.js/index)).

For offline and reproducible runs:

- Models are cached on disk after the first download, and the cache location can be changed with `env.cacheDir`.
- `env.localModelPath` points at local model files, and `env.allowRemoteModels = false` turns off Hub downloads ([Node tutorial](https://huggingface.co/docs/transformers.js/tutorials/node)).
- `from_pretrained` accepts a `revision` (branch, tag or commit id) and `local_files_only`, so a model can be pinned to a commit ([hub utils](https://huggingface.co/docs/transformers.js/api/utils/hub)).

**ONNX Runtime for Node.** It ships prebuilt binaries with CPU support on Windows, Linux and macOS, each on x64 and arm64. CUDA is available on Linux x64 only ([ONNX Runtime docs](https://onnxruntime.ai/docs/get-started/with-javascript/node.html)). A plain `npm install` therefore covers a demo on common machines.

**Hugging Face Hub access without a key.**

- Public, non-gated repositories download anonymously.
- Anonymous downloads are limited to 3,000 resolver requests per 5 minutes per IP (values from September 2025, "subject to change") ([Hub rate limits](https://huggingface.co/docs/hub/rate-limits)).
- `google/embeddinggemma-300m` is gated (manual approval), but its ONNX conversion `onnx-community/embeddinggemma-300m-ONNX` is not gated, though it remains under the Gemma licence. The other repositories in § 3 are not gated (Hub API `gated` field).

**Other TypeScript routes.**

- `fastembed` (npm 3.0.0, `qdrant-labs/fastembed-js`) wraps ONNX Runtime, but its README lists only seven models (bge-small/base v1.5, all-MiniLM-L6-v2, multilingual-e5-large and a few older ones) and no rerankers. It pins `onnxruntime-node` 1.21.0 ([README](https://github.com/qdrant-labs/fastembed-js)).
- GGUF builds exist for EmbeddingGemma, voyage-4-nano and jina-embeddings-v5 (Hub search). They would run through llama.cpp bindings or a separate Ollama service. This route was not investigated: it adds a native runtime or a second process.

**Rerankers from TypeScript.** Cross-encoders load with `AutoTokenizer` plus `AutoModelForSequenceClassification`, and query and document go in as a `text_pair`. The model cards of mxbai-rerank-xsmall-v1, jina-reranker-v1-turbo-en and gte-reranker-modernbert-base show this in Transformers.js ([mxbai](https://huggingface.co/mixedbread-ai/mxbai-rerank-xsmall-v1), [jina](https://huggingface.co/jinaai/jina-reranker-v1-turbo-en), [gte](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base)), and § 6 measured it.

LLM-style rerankers work differently. Qwen3-Reranker-0.6B scores a pair from the logits of the "yes" and "no" tokens ([card](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)), so it needs the causal-LM path instead of sequence classification. Its ONNX build `onnx-community/Qwen3-Reranker-0.6B-ONNX` exists (q4 995 MB, q8 1.2 GB) but was not tested.

## 3. Local embedding models

Parameter counts come from the Hub's safetensors metadata; dimensions and max positions from each `config.json` or `sentence_bert_config.json`. Licences come from Hub tags or the MTEB model metadata. ONNX sizes are the 8-bit (`model_quantized`) file, the one Transformers.js loads with `dtype: 'q8'`.

| Model | Params | Dims | Max input (tokens) | Licence | ONNX build for Transformers.js (q8 size) | Notes |
|---|---|---|---|---|---|---|
| [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | 23M | 384 | 256 | Apache-2.0 | `Xenova/all-MiniLM-L6-v2` (23 MB) | Oldest and fastest; a baseline |
| [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) | 33M | 384 | 512 | MIT | `Xenova/bge-small-en-v1.5` (34 MB) | Default model of fastembed |
| [BAAI/bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5) | 109M | 768 | 512 | MIT | `Xenova/bge-base-en-v1.5` (110 MB) | |
| [Snowflake/snowflake-arctic-embed-xs](https://huggingface.co/Snowflake/snowflake-arctic-embed-xs) / [-s](https://huggingface.co/Snowflake/snowflake-arctic-embed-s) | 23M / 33M | 384 | 512 | Apache-2.0 | In repository (23 / 34 MB) | |
| [Snowflake/snowflake-arctic-embed-m-v2.0](https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0) | 305M | 768 | 8,192 | Apache-2.0 | In repository (311 MB) | Multilingual |
| [nomic-ai/nomic-embed-text-v1.5](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) | 137M | 768 | 8,192 | Apache-2.0 | In repository (137 MB) | |
| [Alibaba-NLP/gte-modernbert-base](https://huggingface.co/Alibaba-NLP/gte-modernbert-base) | 149M | 768 | 8,192 | Apache-2.0 | In repository (150 MB) | ModernBERT |
| [ibm-granite/granite-embedding-small-english-r2](https://huggingface.co/ibm-granite/granite-embedding-small-english-r2) | 48M | 384 | 8,192 | Apache-2.0 | `onnx-community/granite-embedding-small-english-r2-ONNX` (52 MB) | ModernBERT; card says it does not train on MS-MARCO |
| [ibm-granite/granite-embedding-english-r2](https://huggingface.co/ibm-granite/granite-embedding-english-r2) | 149M | 768 | 8,192 | Apache-2.0 | `onnx-community/granite-embedding-english-r2-ONNX` (158 MB, not tagged for Transformers.js, not tested) | ModernBERT |
| [mixedbread-ai/mxbai-embed-xsmall-v1](https://huggingface.co/mixedbread-ai/mxbai-embed-xsmall-v1) | 24M | 384 | 4,096 | Apache-2.0 | In repository (24 MB) | |
| [mixedbread-ai/mxbai-embed-large-v1](https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1) | 335M | 1,024 | 512 | Apache-2.0 | In repository (337 MB) | |
| [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m) | 308M | 768 | 2,048 | Gemma terms | `onnx-community/embeddinggemma-300m-ONNX` (309 MB) | Original repository is gated |
| [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2) | 744M total, 270M text | 768 (MRL 512/256/128) | 8,192 | Apache-2.0 | `onnx-community/embeddinggemma-2-ONNX`, text model 314 MB | Multimodal. Prompts `task: search result \| query: …` / `title: none \| text: …`. The card says not to run it in float16 ([card](https://gemma.ai/models/embeddinggemma/model-card-v2/), [ONNX card](https://huggingface.co/onnx-community/embeddinggemma-2-ONNX)) |
| [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 596M | 1,024 (MRL 32–1,024) | 32K | Apache-2.0 | `onnx-community/Qwen3-Embedding-0.6B-ONNX` (614 MB) | Queries take a one-sentence instruction; last-token pooling ([ONNX card](https://huggingface.co/onnx-community/Qwen3-Embedding-0.6B-ONNX)) |
| [MongoDB/voyage-4-nano](https://huggingface.co/MongoDB/voyage-4-nano) | 346M (card: 180M non-embedding + 160M embedding) | 2,048 default (1,024/512/256) | 32K | Apache-2.0 | `onnx-community/voyage-4-nano-ONNX` (422 MB, not tagged for Transformers.js) | Shares the embedding space of the hosted voyage-4 models (§ 8). The ONNX build ran a forward pass in Transformers.js 4.3.2 (§ 5); whether its output matches the reference model was not verified |
| [jinaai/jina-embeddings-v5-text-nano](https://huggingface.co/jinaai/jina-embeddings-v5-text-nano) | 212M | 768 | 8,192 | **CC BY-NC 4.0** | `jinaai/jina-embeddings-v5-text-nano-retrieval` has ONNX (247 MB, not tagged for Transformers.js, not tested) | Non-commercial weights; Jina sells a commercial licence ([Jina](https://jina.ai/embeddings/)) |

Static embeddings such as `minishlab/potion-*` (model2vec) are much faster but score far lower on these tasks (CQADupStack-Unix 19.8 for potion-retrieval-32M), so they are left out.

## 4. Quality on benchmarks close to the task

**No public benchmark measures duplicate GitHub issues.** MTEB has two families of tasks close to this one.

- **Duplicate questions:**
  - CQADupStack retrieves duplicate questions on StackExchange subforums. The technical ones are Unix, Programmers, Webmasters, WordPress and Android ([task](https://github.com/embeddings-benchmark/mteb/blob/main/mteb/tasks/retrieval/eng/cqa_dupstack_unix_retrieval.py)), scored by nDCG@10.
  - StackOverflowDupQuestions covers Java, JavaScript and Python questions; AskUbuntuDupQuestions covers manually annotated AskUbuntu pairs. Both are reranking tasks scored by MAP@1000.
  - SprintDuplicateQuestions covers duplicate questions from the Sprint community, a pair classification scored by max AP.
- **Technical text:** StackOverflowQA retrieves answers that mix text and code (nDCG@10). FreshStackRetrieval goes from a natural-language task to code (nDCG@10).

Several MTEB tasks built from SWE-bench use GitHub issues as queries, but they retrieve code files, not duplicate issues.

The table reads the `main_score` of each task from the [`embeddings-benchmark/results`](https://github.com/embeddings-benchmark/results) repository on 2026-11-20. Two aggregates are computed here:

- **Tech mean** is the average of the five technical CQADupStack subforums.
- **MTEB(eng, v2) retrieval** is the average of its 10 retrieval tasks, shown only when all 10 are present. As a check, Qwen3-Embedding-0.6B comes out at 61.8 here, against 61.83 on its model card.

| Model | CQADupStack tech mean (5) | CQADupStack Unix | StackOverflowDupQuestions | AskUbuntuDupQuestions | SprintDuplicateQuestions | StackOverflowQA | MTEB(eng, v2) retrieval (10) |
|---|---|---|---|---|---|---|---|
| **Local** | | | | | | | |
| all-MiniLM-L6-v2 | 41.5 | 41.3 | 50.8 | 63.5 | 94.5 | 84.0 | 42.9 |
| bge-small-en-v1.5 | 38.6 | 38.8 | 53.6 | 62.6 | 96.7 | 78.0 | 53.9 |
| bge-base-en-v1.5 | 42.3 | 42.2 | 54.6 | 62.1 | 96.4 | 80.2 | 54.8 |
| snowflake-arctic-embed-xs | 41.0 | 40.1 | 50.2 | 60.3 | 95.0 | 82.8 | 52.6 |
| snowflake-arctic-embed-s | 42.6 | 42.5 | 50.2 | 61.1 | 95.3 | 83.0 | 54.9 |
| snowflake-arctic-embed-m-v2.0 | 47.9 | 47.8 | 54.3 | 62.3 | 96.0 | 90.7 | 58.4 |
| nomic-embed-text-v1.5 | 38.4 | 36.8 | 50.5 | 61.7 | 96.0 | 63.6 | 48.0 |
| gte-modernbert-base | 43.6 | 43.4 | 54.9 | 63.3 | 97.4 | 90.9 | – |
| granite-embedding-small-english-r2 | – | 51.1 | 54.0 | 64.8 | 94.9 | 90.0 | 53.9 |
| granite-embedding-english-r2 | – | 52.9 | 54.3 | 66.5 | 94.6 | 91.8 | 56.4 |
| mxbai-embed-xsmall-v1 | 42.1 | 41.8 | – | – | – | – | – |
| mxbai-embed-large-v1 | 41.2 | 41.8 | 55.9 | 63.5 | 96.8 | 80.9 | 55.4 |
| embeddinggemma-300m | 42.1 | 41.5 | – | 63.0 | 97.0 | 86.5 | 55.7 |
| embeddinggemma-2 | – | 40.9 | – | – | 96.5 | 87.3 | 51.3 |
| Qwen3-Embedding-0.6B | 46.5 | 51.5 | 54.5 | 65.1 | 94.1 | 90.0 | 61.8 |
| jina-embeddings-v5-text-nano (CC BY-NC) | 45.1 | 47.4 | – | – | 95.5 | 92.3 | 58.8 |
| **Hosted** | | | | | | | |
| openai/text-embedding-3-small | 43.4 | 43.5 | 51.5 | 62.2 | 94.6 | 88.7 | 53.5 |
| openai/text-embedding-3-large | 47.8 | 50.0 | 55.1 | 65.0 | 92.3 | 92.4 | 58.0 |
| Cohere embed-english-v3.0 | 41.9 | 40.6 | 52.5 | 61.7 | 96.3 | 89.3 | 55.7 |
| google/gemini-embedding-001 | – | 53.7 | – | 64.2 | 96.9 | – | 64.3 |
| amazon Titan text embeddings v2 | 46.6 | 46.5 | 54.8 | 63.3 | 92.9 | – | – |

The newer hosted models (the voyage-4 family, Cohere embed-v5.0, gemini-embedding-2) have no public results on these tasks in that repository. The one task they share with the rest is FreshStackRetrieval (NL task → code, nDCG@10), on which the scores are:

- **Hosted:** voyage-4-large 49.3, voyage-4 46.6, Cohere embed-v5.0-pro 46.5, voyage-4-lite 43.6, voyage-3.5 43.1, Cohere embed-v5.0-fast 42.8, gemini-embedding-001 39.8, Cohere embed-v4.0 37.1, text-embedding-3-large 32.8, text-embedding-3-small 29.6.
- **Local, for reference:** jina-v5-text-nano 38.3, granite-english-r2 34.0, granite-small-english-r2 32.9, embeddinggemma-300m 30.4, bge-small 25.1, all-MiniLM-L6-v2 22.8.

How to read these numbers:

- **Mixed runs.** The scores come from different MTEB versions (1.12 to 2.26). Some are self-reported "external" results copied from model cards: bge's StackOverflowDupQuestions, and most Snowflake and Titan rows. They are indicative, not a controlled comparison.
- **Possible contamination.** StackExchange data is common in embedding training sets, so CQADupStack scores may be inflated for some models. The Granite r2 card lists its training sources without naming StackExchange ([card](https://huggingface.co/ibm-granite/granite-embedding-small-english-r2)).
- **Short texts.** These datasets are mostly short question titles or posts. GitHub issues are longer, follow templates, and carry stack traces and logs (§ 1). The long-context models (8K–32K) only gain on this task if more of each issue is embedded, and that costs CPU (§ 5).
- **Only CQADupStack separates models.** On StackOverflowDupQuestions, AskUbuntuDupQuestions and SprintDuplicateQuestions almost every model sits within about 3–5 points of the others, so those tasks barely tell them apart.

The project's replay eval on the target repository is the only measurement of this task.

## 5. Speed on a laptop CPU (measured)

**Setup:**

- **Machine:** Intel Core i7-1255U, a 2022 15 W laptop part with 2 performance and 8 efficiency cores (12 threads), 7.6 GB RAM, under WSL2.
- **Software:** Node 24.16, Transformers.js 4.3.2, `onnxruntime-node` 1.30.0, default thread settings, batches of 8.
- **Input:** a deterministic random sample of the 800 issues from § 1, sorted by length to limit padding (as a batch ingestion would), cut at the stated token cap.
- **Measured:** the model's forward pass. Pooling and normalization are negligible next to it.

Repeated runs of the same configuration varied by about ±25% (bge-small, q8, 512: 6.5 and 8.4 issues/s; all-MiniLM-L6-v2: 27.6–33.0 issues/s), and forcing the thread count to 4 or 12 made it slower. The "50,000 issues" column is an **estimate** extrapolated from the measured rate, not a measured run.

| Model (ONNX repo) | dtype | Token cap | Issues per second | Estimated time for 50,000 issues |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | q8 | 256 | 28–33 | 25–30 min |
| all-MiniLM-L6-v2 | fp32 | 256 | 16 | 51 min |
| bge-small-en-v1.5 | q8 | 256 | 15 | 55 min |
| bge-small-en-v1.5 | q8 | 512 | 6.5–8.4 | 1.7–2.1 h |
| bge-small-en-v1.5 | fp32 | 512 | 3.7 | 3.8 h |
| granite-embedding-small-english-r2 | q8 | 256 | 12.7 | 1.1 h |
| granite-embedding-small-english-r2 | q8 | 512 | 5.3 | 2.6 h |
| granite-embedding-small-english-r2 | q8 | 2,048 | 1.8 | 7.7 h |
| bge-base-en-v1.5 | q8 | 512 | 2.0 | 6.8 h |
| nomic-embed-text-v1.5 | q8 | 512 | 2.2 | 6.2 h |
| snowflake-arctic-embed-m-v2.0 | q8 | 512 | 2.6 | 5.3 h |
| gte-modernbert-base | q8 | 512 | 1.2 | 11.5 h |
| gte-modernbert-base | q8 | 2,048 | 0.5 | 27 h |
| embeddinggemma-300m | q8 | 512 | 1.3 | 10.4 h |
| embeddinggemma-2 (text) | q8 | 512 | 1.0 | 14.4 h |
| Qwen3-Embedding-0.6B | q8 | 512 | 0.4 | 34 h |
| voyage-4-nano | q8 | 512 | 0.5–0.7 | 20–27 h |

What follows from this:

- **Query time is not the bottleneck.** One new issue embeds in about 0.03–0.2 s with the small models and about 2.5 s with Qwen3-Embedding-0.6B, at batch-of-one cost roughly equal to the per-issue rates above.
- **Indexing the corpus is.** With a small model at 256–512 tokens it is an hour or two on a laptop, and with anything at or above 300M parameters it runs overnight or longer. A GitHub-hosted runner for a public repository has 4 CPUs and 16 GB RAM ([GitHub docs](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)), so expect CI to be slower than this laptop (not measured). Re-embedding the full corpus on every CI run is impractical with anything above the smallest models, and computed vectors would need to be cached (§ 8).
- **Long-context models cost more on long issues.** granite-small-r2 went from 5.3 to 1.8 issues/s when the cap moved from 512 to 2,048 tokens.
- **Quantization roughly doubles throughput.** `q8` ran about twice as fast as `fp32` on this CPU. Its effect on retrieval quality was not measured.

## 6. Local rerankers

All the models below loaded with `AutoModelForSequenceClassification` and scored pairs in Transformers.js 4.3.2, with the same setup as § 5. A pair is a short query plus an issue cut at the stated cap. In duplicate search both sides of the pair are issues, but the pair is cut at the same total cap, so the cost per pair is about the same.

| Model | Params | Max input | Licence | ONNX (q8 size) | Pairs/s (cap 512) | Per query, 50 candidates | Reported quality |
|---|---|---|---|---|---|---|---|
| [cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) | 23M | 512 | Apache-2.0 | `Xenova/ms-marco-MiniLM-L-6-v2` (23 MB) | 14.3 (32.6 at cap 256) | 3.5 s (1.5 s at 256) | BEIR (17) nDCG@10 48.64, per the jina card |
| [jinaai/jina-reranker-v1-turbo-en](https://huggingface.co/jinaai/jina-reranker-v1-turbo-en) | 38M | 8,192 | Apache-2.0 | In repository (38 MB) | 11.3 | 4.4 s | BEIR (17) 49.60; LoCo 69.21 |
| [jinaai/jina-reranker-v1-tiny-en](https://huggingface.co/jinaai/jina-reranker-v1-tiny-en) | 33M | 8,192 | Apache-2.0 | In repository (33 MB) | not measured | – | BEIR (17) 48.54 |
| [mixedbread-ai/mxbai-rerank-xsmall-v1](https://huggingface.co/mixedbread-ai/mxbai-rerank-xsmall-v1) | 71M | 512 | Apache-2.0 | In repository (87 MB) | 4.2 | 12 s | BEIR (11) nDCG@10 43.9 (its card); BEIR (17) 48.80 (jina card) |
| [BAAI/bge-reranker-base](https://huggingface.co/BAAI/bge-reranker-base) | 278M | 512 | MIT | `Xenova/bge-reranker-base` (279 MB) | 3.1 | 16 s | BEIR (11) 41.6 (mxbai card); BEIR (17) 47.89 (jina card) |
| [Alibaba-NLP/gte-reranker-modernbert-base](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base) | 150M | 8,192 | Apache-2.0 | In repository (151 MB) | 2.0 | 25 s | BEIR (15) 56.73 vs 55.33 for its embedding sibling; CoIR 79.99 |
| [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 568M | 8,192 | Apache-2.0 | `onnx-community/bge-reranker-v2-m3-ONNX` (571 MB) | 0.9 | 56 s | MTEB-R 57.03, MTEB-Code 41.38 (Qwen3-Reranker card) |
| [Qwen/Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | 596M | 32K | Apache-2.0 | `onnx-community/Qwen3-Reranker-0.6B-ONNX` (q8 1.2 GB) | not tested (yes/no logits, § 2) | – | MTEB-R 65.80, MTEB-Code 73.42 on Qwen3-Embedding-0.6B top-100 |
| [jinaai/jina-reranker-v2-base-multilingual](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual) | 278M | – | **CC BY-NC 4.0** | In repository (280 MB) | not measured | – | – |

Reported quality comes from model cards with different dataset subsets, so only rows from the same card compare.

What follows from this:

- **Yes, a cross-encoder runs locally from TypeScript.** The fastest models rerank 50 candidates in 1.5–4.5 s on this laptop, which suits an interactive demo.
- **Reranking a whole replay eval is costly.** For example, 2,000 replayed issues × 50 candidates is 100,000 pairs: about 2 hours with ms-marco-MiniLM-L6-v2 at cap 512, and over a day with bge-reranker-v2-m3 (estimates).
- **None of these rerankers was trained on duplicate detection.** They were trained on passage relevance (MS MARCO and similar), and none reports results on the duplicate tasks of § 4. Whether reranking improves duplicate recall over hybrid search is for the eval to show.

## 7. Hosted APIs

### Embeddings

Costs are for 50,000 issues × 914 tokens ≈ 45.7M tokens (§ 1). Each provider has its own tokenizer, so treat the figures as ±25%.

| Provider and model | Price per 1M tokens (2026-11-20) | Batch price | Free allowance | Dims | Max input (tokens) | Cost for 50,000 issues | TypeScript client |
|---|---|---|---|---|---|---|---|
| OpenAI `text-embedding-3-small` | $0.02 | 50% off via Batch API | – | 1,536 (shortenable) | 8,192 | **$0.91** ($0.46 batch) | `openai` |
| OpenAI `text-embedding-3-large` | $0.13 | 50% off | – | 3,072 (shortenable) | 8,192 | **$5.94** ($2.97 batch) | `openai` |
| Voyage `voyage-4-lite` | $0.02 | 33% off | 200M tokens | 1,024 (256–2,048) | 32,000 | **$0.91**, within the free tokens | `voyageai` |
| Voyage `voyage-4` | $0.06 | 33% off | 200M tokens | 1,024 (256–2,048) | 32,000 | **$2.74** | `voyageai` |
| Voyage `voyage-4-large` | $0.12 | 33% off | 200M tokens | 1,024 (256–2,048) | 32,000 | **$5.48** | `voyageai` |
| Voyage `voyage-code-4` | $0.12 | 33% off | 200M tokens | 1,024 (256–2,048) | 32,000 | **$5.48** | `voyageai` |
| Cohere `embed-v5.0-fast` | $0.08 | – | Trial key: free, 1,000 calls/month, non-commercial | 2,048 (256–2,048) | 128K | **$3.66** | `cohere-ai` |
| Cohere `embed-v5.0-pro` | $0.12 | – | Same trial key | 2,048 (256–2,048) | 128K | **$5.48** | `cohere-ai` |
| Google `gemini-embedding-001` | $0.15 | $0.075 | Free tier (its data is used to improve Google's products) | 3,072 (128–3,072) | **2,048** | **$6.86** ($3.43 batch) | `@google/genai` |
| Google `gemini-embedding-2` | $0.20 | $0.10 | Free tier (same condition) | 3,072 (128–3,072) | 8,192 | **$9.14** ($4.57 batch) | `@google/genai` |
| Mistral `codestral-embed-2505` | $0.15 | – | – | – | 8K | **$6.86** | `@mistralai/mistralai` |

Sources for the table:

- **OpenAI:** [pricing](https://developers.openai.com/api/docs/pricing), [embeddings guide](https://developers.openai.com/api/docs/guides/embeddings) and [Batch API](https://developers.openai.com/api/docs/guides/batch). The Batch API supports `/v1/embeddings` at a 50% discount, with up to 50,000 inputs per batch. The free tier is 100 RPM and 40,000 TPM ([model page](https://developers.openai.com/api/docs/models/text-embedding-3-small)), which is too slow for a first ingestion.
- **Voyage:** [pricing](https://docs.voyageai.com/docs/pricing), [MongoDB billing](https://www.mongodb.com/docs/voyageai/management/billing/) and [embeddings](https://docs.voyageai.com/docs/embeddings). Requests take up to 1,000 texts each. The Batch API discount is 33% and does not apply to free tokens. Voyage keys are now created in MongoDB Atlas ([Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/embeddings)).
- **Cohere:** prices and trial-key terms from [cohere.com/pricing](https://cohere.com/pricing) (the prices are in the page's embedded data, not a visible table), plus [models](https://docs.cohere.com/docs/models) and [rate limits](https://docs.cohere.com/docs/rate-limits).
- **Google:** [pricing](https://aistudio.google.com/docs/pricing) and [embeddings](https://aistudio.google.com/docs/embeddings).
- **Mistral:** [model page](https://docs.mistral.ai/models/codestral-embed-25-05).

Anthropic does not offer its own embedding model, and its docs point to Voyage ([Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/embeddings)).

Jina's API serves the v5 models, but its page publishes no per-token price ([Jina](https://jina.ai/embeddings/)).

The Vercel AI SDK (`ai` on npm) offers `embed`/`embedMany` for OpenAI, Google, Mistral, Cohere and Bedrock, and wraps models in middleware, but documents no caching ([AI SDK embeddings](https://ai-sdk.dev/docs/ai-sdk-core/embeddings)). Voyage is not in its tables.

Quality notes for hosted models are in § 4. Where public numbers exist on the duplicate tasks, gemini-embedding-001 and text-embedding-3-large lead CQADupStack-Unix, while text-embedding-3-small is level with the small local models. gemini-embedding-001's 2,048-token cap would truncate 8.4% of the sampled issues (counted with cl100k), against 0.9% for 8K-token models and none for 32K.

### Rerankers

| Provider and model | Price (2026-11-20) | Free allowance | Context | Cost per replayed issue (50 candidates) | Cost for 2,000 replayed issues |
|---|---|---|---|---|---|
| Voyage `rerank-3` | $0.05 per 1M tokens | 200M tokens | 32K (query ≤ 8K) | about $0.002 | **about $4**, within the free tokens |
| Voyage `rerank-3-lite` | $0.02 per 1M tokens | 200M tokens | 32K (query ≤ 8K) | about $0.0008 | **about $1.60** |
| Cohere `rerank-v5.0-pro` | $0.05 per 1M tokens | Trial key: 10 requests/min | 32K | Not computed: token accounting not documented | – |
| Cohere `rerank-v5.0-fast` | $0.02 per 1M tokens | Same trial key | 32K | Not computed | – |

Voyage bills reranking as "(query tokens × number of documents) + sum of tokens in all documents" ([MongoDB billing](https://www.mongodb.com/docs/voyageai/management/billing/); [reranker docs](https://docs.voyageai.com/docs/reranker)). Since the query is a whole issue, each query is counted once per candidate. With the query and the candidates each cut to about 400 tokens, 50 candidates come to 400 × 50 + 50 × 400 ≈ 40,000 tokens per replayed issue.

Cohere moved Rerank 5 to per-token pricing (data of [cohere.com/pricing](https://cohere.com/pricing)). Its older pricing counted "one query with up to 100 documents" as a search unit, and split documents over 500 tokens into chunks. Whether Rerank 5 counts the query per document was not found.

The AI SDK's `rerank` function supports Cohere, Amazon Bedrock and Together.ai models, but not Voyage ([AI SDK reranking](https://ai-sdk.dev/docs/ai-sdk-core/reranking)).

## 8. Caching for a keyless demo and CI

What can be cached:

- **Corpus vectors.** A vector is a function of (provider, model, model version, output dimensions, input type or prompt, text), so it can be computed once, stored under a hash of those fields, and reused.
- **Storage for 50,000 vectors:**

  | Dims | float32 | int8 | binary |
  |---|---|---|---|
  | 384 | 77 MB | 19 MB | 2.4 MB |
  | 768 | 154 MB | 38 MB | 4.8 MB |
  | 1,024 | 205 MB | 51 MB | 6.4 MB |
  | 3,072 | 614 MB | 154 MB | 19 MB |

  Voyage returns int8 and binary vectors directly. Matryoshka models (voyage-4, Qwen3-Embedding, EmbeddingGemma 2, the OpenAI and Gemini APIs) can be truncated to fewer dimensions.
- **Where to store them.** GitHub blocks files over 100 MiB in a repository but does not cap the total size of release assets ([GitHub docs](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)). GitHub Actions caches hold 10 GB per repository and drop entries unused for 7 days ([GitHub docs](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)). Whether issue text and vectors derived from it may be redistributed is a separate question for the data-redistribution decision.
- **Local model files.** Downloading them needs no key. They can be pinned to a Hub commit with `revision` and kept in the Actions cache. Sizes range from 23 MB (MiniLM q8) to 614 MB (Qwen3-Embedding-0.6B q8).

The query side is the hard part. The demo has to embed an issue that is not in the cache. The options are:

1. **Local model end to end.** Corpus and queries both use the same local ONNX model. No key is ever needed, and the corpus vectors can be shipped or rebuilt (§ 5 gives the CPU time). This ties retrieval quality to the local model.
2. **Hosted corpus, recorded queries.** A run with a key records the vectors of every query the demo and CI will use: the replayed eval issues and a fixed set of demo issues. Keyless runs replay them and fail on a cache miss. A free-text new issue in the demo would need a key.
3. **Hosted voyage-4 corpus, local voyage-4-nano queries.** Voyage states that "all embeddings created with the 4 series are compatible with each other" ([embeddings docs](https://docs.voyageai.com/docs/embeddings)). The voyage-4-nano card says embeddings across the family "can be directly compared and used interchangeably" ([card](https://huggingface.co/MongoDB/voyage-4-nano)). voyage-4-nano is open-weight (Apache-2.0), with 2,048 default dimensions against 1,024 for the hosted models; the dimension must match on both sides. Its ONNX build (`onnx-community/voyage-4-nano-ONNX`, q8) ran in Transformers.js 4.3.2 at 0.5–0.7 issues per second at cap 512, which is about 1.5–2 s per query on the laptop. Whether that build reproduces the reference embeddings, and so lands in the hosted space, was not verified: checking needs a Voyage key. No public MTEB results for voyage-4-nano were found in the results repository.
4. **Hosted reranker.** Results can be recorded the same way, keyed by query, candidate list and model, but any change to the candidate list misses the cache. A local cross-encoder (§ 6) avoids the key.

Replayed history fits recording well, because the eval queries are a fixed set known in advance. Only a free-text demo query needs a model at run time. Recording and replaying model calls is listed under "Not yet specified" in the map.

## 9. Trade-offs, without choosing

| Option | What it buys | What it costs |
|---|---|---|
| Small local model (MiniLM, bge-small, granite-small-r2, arctic-xs/s) | No key anywhere; 23–52 MB download; corpus in about 0.5–2.6 h on a laptop; subsecond queries | Lower scores on CQADupStack, except granite-small-r2 at 51.1 on Unix; 512-token cap on most, which truncates 55% of issues |
| Mid-size local model (bge-base, arctic-m-v2.0, gte-modernbert, granite-r2, nomic) | Better general retrieval; 8K context on several | 5–12 h corpus on a laptop at 512 tokens; CI cannot re-embed, so vectors must be cached |
| Large local model (EmbeddingGemma, Qwen3-Embedding-0.6B) | Best local MTEB scores (Qwen3: 61.8 retrieval, 51.5 Unix) | 10–34 h corpus on a laptop; 300–600 MB model; Gemma licence for EmbeddingGemma 300m |
| Hosted embeddings | Highest scores where measured (gemini-001, OpenAI 3-large); corpus in minutes for under $10 | Key needed to ingest and to embed free-text queries; needs recording for CI and the demo; models get deprecated and replaced |
| voyage-4 hosted + voyage-4-nano local | Hosted-quality corpus with a keyless query path | Compatibility untested here; nano is 346M parameters with 32K context, so heavier queries; Voyage-specific |
| Local cross-encoder | Keyless reranking; 1.5–4.5 s per query with small models | Not trained on duplicates; slow over a full replay eval |
| Hosted reranker | Long context (32K); about $2–4 per 2,000 replayed issues on Voyage | Key needed; results cacheable only for fixed candidate lists |

## 10. Open caveats

- **No direct measurement.** No benchmark here measures duplicate GitHub issues, and the MTEB numbers are mixed versions and partly self-reported (§ 4).
- **One machine, ±25% noise.** The speeds come from one laptop under WSL2. Apple Silicon, desktop CPUs and the 4-CPU GitHub runner were not measured, and nor was WebGPU in Node.
- **Not tested here:** granite-embedding-english-r2 ONNX, the jina v5 ONNX builds, Qwen3-Reranker in Transformers.js, whether the voyage-4-nano ONNX build matches the reference model and the hosted voyage-4 space, and whether quantization changes retrieval quality.
- **Comments not counted.** The token counts cover title plus body. Embedding comments as well would raise both API cost and CPU time.
- **Prices change.** All prices are as of 2026-11-20. Cohere's prices come from the data behind its pricing page, not from a published table, and Jina publishes no per-token price.
- **Terms not checked.** Each provider's terms on storing and redistributing returned vectors were not reviewed. Google's free tier uses submitted data to improve its products.

## Method and reproducibility

The throwaway scripts lived outside the repository. They did four things:

- **Issue sample:** fetched with `gh api search/issues` (§ 1).
- **Token counts:** `js-tiktoken` and the Transformers.js tokenizer of `Xenova/bge-small-en-v1.5`.
- **Model metadata:** read from the Hugging Face API (`/api/models/<id>?blobs=true`, `config.json`, `sentence_bert_config.json`).
- **MTEB scores:** read from the per-task JSON files of `embeddings-benchmark/results` (`results/<org>__<model>/<revision>/<Task>.json`, field `main_score`).

The CPU benchmark loaded each model with `AutoModel` or `AutoModelForSequenceClassification` and `dtype: 'q8'` or `'fp32'` on `device: 'cpu'`. It warmed up once, then timed the forward passes over the sorted sample in batches of 8.
