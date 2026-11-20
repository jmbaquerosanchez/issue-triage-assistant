# Stores with hybrid search for a local TypeScript tool

> **Snapshot, 2026-11-20.** This report records what its sources said on that date and is not updated. Later research supersedes it by linking back here.

Research for ticket #8 of the phase-1 map (#2). Question: which embedded stores can back hybrid search (BM25 keyword search plus vector search, fused) for a local, single-user tool written in TypeScript, given that every indexed piece carries a date and every query must only see what existed before a cutoff?

- **Date:** 2026-11-20. Versions, stability labels and runtime support move fast; the facts below were true on that date.
- **Method:** official docs, READMEs, release notes, source code and npm registry data for each option, plus throwaway local checks in a scratch directory outside the repo (§ 9). Statements marked **observed** come from those checks and are not documented anywhere; everything else cites its source.
- **Scope:** options and trade-offs only. The store is chosen in #12 and the runtime in #10. Engines that run as a separate server process are out of scope: the ticket asks for something embedded in a local tool.

## Summary

| Option | TypeScript binding (version, weekly npm downloads) | Node / Bun / Deno | BM25 | Vector search | Fusion | Date filter with vector search | Ships as one file |
|---|---|---|---|---|---|---|---|
| **SQLite + FTS5 + sqlite-vec** | `better-sqlite3` 13.2.0 (17.9 M), `node:sqlite` (Release candidate), `bun:sqlite`; extension `sqlite-vec` 0.1.9 (1.9 M), pre-v1 | all three, observed on Linux x64 | FTS5 `bm25()`, built in | `vec0`: exact scan in the stable release; ANN only in an alpha | by hand in SQL (RRF in one query) | **pre-filter**: metadata column applied during the KNN scan, exact recall | yes, a single `.db` file |
| **libSQL** | `@libsql/client` 0.18.0 (6.1 M), native `libsql` 0.5.29 | all three, observed; the README claims all three | FTS5 (fork of SQLite 3.45.1) | native vector types; exact scan, or a DiskANN index | by hand in SQL | exact scan + `WHERE`: pre-filter; DiskANN `vector_top_k`: **post-filter** | yes, a single `.db` file |
| **DuckDB + fts + vss** | `@duckdb/node-api` 2.0.0-r.1 (4.2 M), DuckDB 2.0.0 | all three, observed | `fts` extension `match_bm25`; index not updated automatically unless `incremental = 1` | exact array distance, or an HNSW index (persistence experimental) | by hand in SQL | exact scan + `WHERE`: pre-filter; HNSW: pre-filter by default since Sept 2026 | yes, a single `.duckdb` file; extensions are fetched separately |
| **LanceDB** | `@lancedb/lancedb` 0.41.0 (0.5 M), Node ≥ 22 | all three, observed; only Node is documented | native FTS index, BM25 | flat (exact) search without an index; IVF/HNSW indexes optional | **built in**: hybrid query + RRF reranker (k = 60) | **pre-filter by default**, on both legs of a hybrid query | no: a directory of files (10 files after one build) |
| **Orama** | `@orama/orama` 3.1.18 (2.1 M), pure TypeScript | all three, observed | built in | brute-force cosine in memory | **built in** `mode: 'hybrid'`: max-normalised weighted sum, not RRF | pre-filter (`where` builds the candidate set before the scan) | one serialised file, but the whole index lives in memory, and persisting 50k synthetic issues failed (§ 5) |
| **PGlite + pgvector + pg_textsearch** | `@electric-sql/pglite` 0.5.17 (44.6 M), Postgres 18.7 in WASM; pgvector 0.8.7, pg_textsearch 1.5.1 | all three, observed in memory; docs list filesystem storage for Node and Bun | `pg_textsearch` `bm25` index | pgvector, exact or HNSW/IVFFlat | by hand in SQL | exact + `WHERE`: pre-filter; HNSW: post-filter unless iterative scans are on | a data directory, or a single `.tar.gz` from `dumpDataDir()` |

Measured on a synthetic corpus of **50,000 pieces, 384-dimensional float32 vectors and about 1.25 KB of text each** (§ 9; single runs on a WSL2 machine, indicative only):

| Option | Build | Size | Hybrid query, 50 % visible | Hybrid query, 5 % visible |
|---|---|---|---|---|
| SQLite + FTS5 + sqlite-vec (`better-sqlite3`) | 5.8 s | **194.6 MB**, one file | 29 ms | 21 ms |
| libSQL, exact vectors | 9.6 s | **252.7 MB**, one file (533.4 MB with a compressed DiskANN index) | 47–91 ms | 8–11 ms |
| DuckDB, exact vectors | 37 s | **130.0 MB** (214.4 MB with an HNSW index), one file | 220 ms | 140 ms |
| LanceDB, flat vectors | 7.1 s | **132.8 MB**, directory | 128 ms | 133 ms |
| Orama | 39 s | 1.33 GB of JS heap; **could not be persisted** | 59 ms | 9 ms |
| PGlite | 65 s | 404 MB directory, **246.9 MB** as a gzipped dump | 239 ms | 32 ms |

Three facts cut across the rows:

1. **At this scale an exact vector scan took under 250 ms, and it sidesteps the filtered-ANN problem.** Every option answered a date-filtered hybrid query over 50k pieces in under 250 ms without any vector index, and the date filter then simply narrows the scan, so recall stays exact whatever the cutoff (§ 7).
2. **Replaying history sweeps filter selectivity from almost nothing to everything.** An early cutoff leaves a small fraction of the corpus visible, which is exactly where post-filtered ANN indexes return fewer than k results (libSQL's `vector_top_k`, pgvector's HNSW without iterative scans). Pre-filtering stores (sqlite-vec metadata columns, LanceDB, DuckDB vss since September 2026, Orama) and exact scans do not have that problem (§ 7).
3. **BM25 statistics see the future.** In FTS5 the IDF and the average document length are computed over the whole table, not over the rows a `WHERE` lets through ([FTS5 § 5.1.1](https://www.sqlite.org/fts5.html)); pg_textsearch says the same of its index. A piece's keyword score before a cutoff is therefore influenced by documents created after it. No option offers per-query corpus statistics as far as I found (§ 8).

## 1. SQLite + FTS5 + sqlite-vec

### Bindings and runtimes

There are three ways to open SQLite from TypeScript, and sqlite-vec loads into all of them: "`load()` works with `node:sqlite`, `better-sqlite3`, `node-sqlite3`, `jsr:@db/sqlite` (Deno), and `bun:sqlite`" ([sqlite-vec JS docs](https://alexgarcia.xyz/sqlite-vec/js.html)).

- **`better-sqlite3`** 13.2.0 (published 2026-11-14), MIT, 17.9 M downloads a week ([npm](https://www.npmjs.com/package/better-sqlite3)). It "ships with prebuilt binaries and does not compile anything when it's installed", bundles SQLite 3.54.1 and compiles it with `SQLITE_ENABLE_FTS5` ([compilation docs](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/compilation.md)). It "Requires a currently supported Node.js version" ([README](https://github.com/WiseLibs/better-sqlite3)). **Observed:** it also loads under Bun 1.4.5 and Deno 2.9.6 on Linux x64, with sqlite-vec.
- **`node:sqlite`**, built into Node. "Stability: 1.2 - Release candidate" since v25.7.0; unflagged since v23.4.0 and v22.13.0; `loadExtension()` and the `allowExtension` option since v23.5.0 and v22.13.0 ([Node docs](https://nodejs.org/api/sqlite.html)). Node's bundled SQLite is compiled with `SQLITE_ENABLE_FTS5` ([`deps/sqlite/sqlite.gyp`](https://github.com/nodejs/node/blob/main/deps/sqlite/sqlite.gyp)). sqlite-vec's docs ask for Node 23.5.0 or later ([sqlite-vec JS docs](https://alexgarcia.xyz/sqlite-vec/js.html)). Bun lists `node:sqlite` as "Fully implemented" ([Bun Node.js compatibility](https://bun.com/docs/runtime/nodejs-compat)). **Observed:** the same script, with `node:sqlite` and sqlite-vec, ran unchanged on Node 24.16.0 (SQLite 3.53.0), Bun 1.4.5 (3.54.1) and Deno 2.9.6 (3.53.2). On that path the only native piece to install is the sqlite-vec extension.
- **`bun:sqlite`**, Bun only. It loads extensions with `.loadExtension()`, but "By default, macOS ships with Apple's proprietary build of SQLite, which doesn't support extensions", so `Database.setCustomSQLite(path)` must point to another build first ([Bun SQLite docs](https://bun.com/docs/runtime/sqlite)).
- **Deno and native addons in general:** "npm packages using Node-API addons are supported when a local `node_modules/` directory is present", need `--allow-ffi`, and Deno does not run `postinstall` scripts by default ([Deno Node compatibility](https://docs.deno.com/runtime/fundamentals/node/)).

**sqlite-vec maturity.** "`sqlite-vec` is a pre-v1, so expect breaking changes!"; MIT or Apache-2.0; a Mozilla Builders project also sponsored by Fly.io, Turso, SQLite Cloud and Shinkai ([repo](https://github.com/asg017/sqlite-vec)). The latest stable is 0.1.9 (2026-03-31); 0.1.10-alpha.1 (same day) is the "Initial alpha release of `sqlite-vec` with new ANN indexes: rescore, ivf (experimental, not enabled), and DiskANN", and the last alpha, 0.1.10-alpha.4, is from 2026-05-18 ([releases](https://github.com/asg017/sqlite-vec/releases)); the repository has had no push since then. Open packaging issues: platform checks in the npm router package ([#272](https://github.com/asg017/sqlite-vec/issues/272), not reproduced on Linux x64) and installing under Deno on macOS ([#238](https://github.com/asg017/sqlite-vec/issues/238)). It has 1.9 M weekly downloads ([npm](https://www.npmjs.com/package/sqlite-vec)).

### Keyword ranking

FTS5 ships BM25 as the `bm25()` auxiliary function, and the hidden `rank` column holds it by default; "The better the match, the numerically smaller the value returned" ([FTS5 § 5.1.1, § 5.2](https://www.sqlite.org/fts5.html)). Tokenizers: `unicode61` (default), `ascii`, `porter` (a stemming wrapper) and `trigram` (substring matching) (§ 4.3). An *external content* table indexes rows of a normal table without storing the text twice (§ 4.4). Space-separated query terms are combined with AND, so a duplicate-search query has to join its terms with `OR` explicitly.

### Vector search

`vec0` virtual tables store float, int8 and binary vectors ([repo](https://github.com/asg017/sqlite-vec)). A KNN query is `WHERE embedding MATCH :q AND k = :k`, with `distance_metric=cosine` set per column (L2 by default) ([KNN docs](https://alexgarcia.xyz/sqlite-vec/features/knn.html)). In the stable 0.1.9 the KNN is a full scan; ANN indexes exist only in the 0.1.10 alphas (release notes above).

### Fusion

None built in. Alex Garcia's post shows three fusions in plain SQL: keyword-first, **reciprocal rank fusion** (both searches as CTEs, a full outer join, `1/(rrf_k + rank)` summed, `rrf_k = 60`) and re-ranking keyword hits by vector distance ([Hybrid full-text search and vector search with SQLite](https://alexgarcia.xyz/blog/2024/sqlite-vec-hybrid-search/index.html), 2024-10-02). **Observed:** the RRF query is about 15 lines and needs `FULL OUTER JOIN` (SQLite 3.39+).

### Date filter

- **Vector leg:** a `vec0` *metadata column* (`created_at integer`) can be constrained in the KNN query, and sqlite-vec will "recognize and apply during the KNN calculation" those constraints; operators `=`, `!=`, `>`, `>=`, `<`, `<=`; up to 16 metadata columns ([vec0 docs](https://alexgarcia.xyz/sqlite-vec/features/vec0.html)). That is a pre-filter: **observed**, `created_at < cutoff AND k = 20` returned 20 rows with only 5 % of the corpus visible. *Partition keys* (up to 4) shard the index and restrict the search on `=`; the docs show a date-range example and warn against over-sharding ("hundreds of vectors" per value). *Auxiliary* columns cannot appear in a KNN `WHERE`.
- **Keyword leg:** FTS5 has no metadata filtering of its own ("FTS5 tables perform a full search across the entire dataset everytime", per the hybrid-search post above); the date filter is a join on the content table before `ORDER BY rank LIMIT k`, which is exact.

### Shipping and size

One database file. **Observed** at 50k × 384: 194.6 MB, of which `vec0` 78.7 MB (≈ the raw 76.8 MB of float32 vectors), the issues table with its text 68.4 MB, and the FTS5 index 45.2 MB.

## 2. libSQL

"**libSQL** (this repository) is an open-source fork of SQLite"; the same team now builds Turso, a Rust rewrite, and "**If you're starting a new project, you probably want to look into Turso.** libSQL is actively maintained, but new features are being developed in Turso" ([libSQL README](https://github.com/tursodatabase/libsql)). The embedded client "Supports Bun, Deno, and Node on macOS, Linux, and Windows" ([libsql-js README](https://github.com/tursodatabase/libsql-js)); an open Bun bug turns `SqliteError` into a `TypeError` on local files ([libsql-js#187](https://github.com/tursodatabase/libsql-js/issues/187)). **Observed:** `@libsql/client` 0.18.0 with a `file:` URL ran on Node, Bun and Deno; it reports SQLite 3.45.1 with FTS5 compiled in.

- **Keyword:** FTS5, as in § 1.
- **Vector:** native column types `FLOAT64`, `FLOAT32`, `FLOAT16`, `FLOATB16`, `FLOAT8`, `FLOAT1BIT`; exact search with `vector_distance_cos(...) ORDER BY ... LIMIT`; approximate search with a DiskANN index (`libsql_vector_idx`) queried through `vector_top_k(index, vector, k)`, which "returns the ROWID" of the k neighbours ([Turso vector docs](https://docs.turso.tech/features/ai-and-embeddings)).
- **Date filter:** with the exact scan, a plain `WHERE created_at < ?` (pre-filter, exact). With DiskANN, the documented example joins `vector_top_k` back to the table and filters in the outer `WHERE`, i.e. after the top k are chosen; the only documented way to restrict the indexed set is a partial index (same page). **Observed** at 50k × 384, asking `vector_top_k` for 20 and then filtering by date returned 9 rows with 50 % of the corpus visible and 1 row with 5 % visible.
- **Index size:** the DiskANN index takes about N × (size of the vector + `max_neighbors` × size of a compressed neighbour), with `max_neighbors` defaulting to 3√D and neighbours **uncompressed** by default (same page). At 384 dimensions that is ≈ 58 neighbours × 1,536 bytes per row, ≈ 4.5 GB for 50k rows; **observed**, the file had grown to 3.9 GB when I stopped the default build. With `compress_neighbors=float1bit` the index took 103 s to build and grew the file from 252.7 MB to 533.4 MB.
- **Shipping:** one file.

## 3. DuckDB with the `fts` and `vss` extensions

### Bindings and runtimes

"The latest stable version of the DuckDB Node.js (Neo) client is 2.0.0", for Linux (glibc and musl), macOS and Windows on x64 and arm64 ([Node Neo overview](https://duckdb.org/docs/2.0/clients/node_neo/overview.html)). The npm package `@duckdb/node-api` (MIT, 4.2 M weekly downloads) is at 2.0.0-r.1, with a `lts-v1.4` tag for the 1.4 line ([npm](https://www.npmjs.com/package/@duckdb/node-api)). A crash opening databases on Bun was fixed in April 2026 ([duckdb-node-neo#151](https://github.com/duckdb/duckdb-node-neo/issues/151)). **Observed:** it ran on Node, Bun and Deno.

The `fts` and `vss` extensions are not in the npm package: `INSTALL` downloads them, and **observed** the first run fetched them over the network. For an offline demo they can be installed from a local `.duckdb_extension` file ([advanced installation methods](https://duckdb.org/docs/2.0/extensions/advanced_installation_methods.html)).

### Keyword ranking

`PRAGMA create_fts_index(table, id, columns..., stemmer = 'porter', stopwords = 'english', ...)` and `match_bm25(id, query, fields, k := 1.2, b := 0.75, conjunctive := 0)`; disjunctive by default. "By default, the FTS index will not update automatically when the input table changes": either create it with `incremental = 1` (needs a `NOT NULL` id) or rebuild it ([full-text search docs](https://duckdb.org/docs/2.0/core_extensions/full_text_search.html)).

### Vector search

`FLOAT[n]` array columns with `array_distance`, `array_cosine_distance` and `array_negative_inner_product`. The `vss` extension adds an HNSW index (`CREATE INDEX ... USING HNSW`), which "can only be created on tables in in-memory databases by default"; persisting it needs `SET hnsw_enable_experimental_persistence = true`, and since "`WAL` recovery is not yet properly implemented for custom indexes" an unexpected shutdown can corrupt it. "Only vectors consisting of `FLOAT`s (32-bit, single precision) are supported", and "The index itself is not buffer managed and must be able to fit into RAM memory" ([vss docs](https://duckdb.org/docs/2.0/core_extensions/vss.html)). An open issue reports HNSW crashes during automatic checkpoints on 1.5.0 ([duckdb-vss#81](https://github.com/duckdb/duckdb-vss/issues/81)).

### Date filter

- Exact scan: `WHERE created_at < ? ORDER BY array_cosine_distance(...) LIMIT k` is exact.
- HNSW: until September 2026 the extension filtered after the index returned its top k; a community fork, `hnsw_acorn`, exists because "filtered queries can return fewer rows than the LIMIT" ([hnsw_acorn](https://duckdb.org/community_extensions/extensions/hnsw_acorn)). [duckdb-vss#89](https://github.com/duckdb/duckdb-vss/pull/89), merged 2026-09-14, adds pre-filtering as the default ("Filters that DuckDB can push into the table scan can now be evaluated during the HNSW search"), with `SET hnsw_prefilter = false` to go back. The official docs do not mention filtering yet. **Observed** on DuckDB 2.0.0 in memory: a date-filtered top 20 through the HNSW index returned 20 rows even with 0.1 % of 50k rows visible. (Recall against the exact answer was low on random vectors, which are a worst case for HNSW; that number says nothing about real embeddings.)

### Fusion

None built in; the same RRF CTEs as in SQLite work in DuckDB SQL.

### Shipping and size

One `.duckdb` file. **Observed** at 50k × 384: 130.0 MB without a vector index, 214.4 MB with the HNSW index persisted. Loading 50k rows through the row-by-row appender with `appendArray` used about 6 GB of RSS in my script; a bulk `INSERT ... SELECT FROM read_json(...)` did not.

## 4. LanceDB

### Bindings and runtimes

`@lancedb/lancedb` 0.41.0 (2026-11-18), Apache-2.0, 0.5 M weekly downloads, `engines: node >= 22`, with prebuilt optional packages for Linux x64 and arm64 (glibc and musl), macOS arm64 and Windows x64 and arm64, and none for Intel macOS ([npm](https://www.npmjs.com/package/@lancedb/lancedb)). I found no mention of Bun or Deno in its docs or issue tracker. **Observed:** the hybrid query below ran on Node, Bun and Deno. Its optional dependencies include `openai` and `@huggingface/transformers`, for its embedding-function registry.

### Keyword ranking

"Full-text search finds documents by matching words and ranks them with BM25", with TypeScript examples (`Index.fts()`, `.fullTextSearch()`); stemming, stop-word removal and accent folding are on by default ([FTS docs](https://docs.lancedb.com/search/full-text-search)). The TypeScript `BaseTokenizer` type includes `"code"`, which "keeps snake_case and camelCase identifiers as single tokens" (`dist/indices.d.ts` in the package). "new rows can remain outside the FTS index until you optimize the table"; queries still scan them (same page).

### Vector search

Without an index the search is exhaustive, with "guaranteed 100% recall"; "For small tables, you can search the vectors directly". Optional indexes: IVF_FLAT, IVF_PQ, IVF_SQ, IVF_RQ, IVF_HNSW_FLAT, IVF_HNSW_PQ, IVF_HNSW_SQ; metrics `l2`, `cosine`, `dot`, `hamming` ([vector search docs](https://docs.lancedb.com/search/vector-search)).

### Fusion

Built in: "Reciprocal Rank Fusion (RRF) is the default", with `table.query().fullTextSearch(q).nearestTo(v).rerank(await rerankers.RRFReranker.create())` ([hybrid search docs](https://docs.lancedb.com/search/hybrid-search)). `RRFReranker.create(k = 60)` is the only reranker shipped in the TypeScript package ([`rrf.ts`](https://github.com/lancedb/lancedb/blob/main/nodejs/lancedb/rerankers/rrf.ts)); a cross-encoder would run in application code.

### Date filter

"Prefiltering, the default, limits the rows eligible for retrieval before search chooses its candidates"; postfiltering "can return fewer than `limit` rows, including zero" ([filtering docs](https://docs.lancedb.com/search/filtering)). "A hybrid query applies its metadata filter to both the vector and full-text searches" ([hybrid search docs](https://docs.lancedb.com/search/hybrid-search)). **Observed:** `.where('created_at < cutoff')` returned 20 hybrid, 20 vector and 20 keyword rows with 5 % of the corpus visible, none after the cutoff.

### Shipping and size

A table is a directory (`data/`, `_versions/`, `_transactions/`, `_indices/`): **observed** 10 files and 132.8 MB at 50k × 384. It can be shipped as an archive but is not a single file, and versions accumulate on every write until the table is optimised.

## 5. Orama

### Bindings and runtimes

Pure TypeScript, Apache-2.0, 2.1 M weekly downloads ([npm](https://www.npmjs.com/package/@orama/orama)). **Observed:** core search ran on Node, Bun and Deno. Release cadence: the last npm release is 3.1.18 (2025-12-19); the repository's `CHANGELOG.md` lists a 3.2.0 dated 2026-06-27 that is not on npm ([CHANGELOG](https://github.com/oramasearch/orama/blob/main/CHANGELOG.md), [npm versions](https://www.npmjs.com/package/@orama/orama?activeTab=versions)). Document ids must be strings (**observed**, `DOCUMENT_ID_MUST_BE_STRING`).

### Search

- **Keyword:** BM25 full-text search, built in ([`components/algorithms.ts`](https://github.com/oramasearch/orama/blob/main/packages/orama/src/components/algorithms.ts)).
- **Vector:** a linear scan of cosine similarity over every stored vector, keeping only those with `similarity >= threshold`; the default threshold is `DEFAULT_SIMILARITY = 0.8` ([`trees/vector.ts`](https://github.com/oramasearch/orama/blob/main/packages/orama/src/trees/vector.ts)). **Observed:** with the default threshold, vector search returned 0 hits on the synthetic corpus; the threshold has to be set for the embedding model in use.
- **Fusion:** `mode: 'hybrid'` normalises each leg by its maximum score and adds them with weights, `text * textWeight + vector * vectorWeight`, 0.5 and 0.5 unless `hybridWeights` is given ([`search-hybrid.ts`](https://github.com/oramasearch/orama/blob/main/packages/orama/src/methods/search-hybrid.ts)). It is not RRF, and the vector leg of a hybrid query uses the same 0.8 default threshold.
- **Date filter:** `where: { created_at: { lt: cutoff } }` computes the matching ids first and passes them to the vector scan as its candidate set ([`search-vector.ts`](https://github.com/oramasearch/orama/blob/main/packages/orama/src/methods/search-vector.ts)): a pre-filter, exact.

### Shipping and size

Everything lives in the JS heap; **observed** 1.33 GB of heap (1.69 GB RSS) after inserting 50k × 384. The persistence plugin serialises to `json`, `dpack`, `binary` (MessagePack) or `seqproto` ([`plugin-data-persistence/src/index.ts`](https://github.com/oramasearch/orama/blob/main/packages/plugin-data-persistence/src/index.ts)). **Observed** on the synthetic corpus: at 50k all four formats failed (`json`: `RangeError: Invalid string length`; `binary`: "Too deep objects in depth 101", already from about 500 documents; `dpack` and `seqproto`: buffer and type errors); `json` worked up to 20k and took about 24.6 KB per piece (492 MB at 20k). A closed upstream issue reports "512MB seems to be the max supported file size for disk persistence plugin" ([orama#851](https://github.com/oramasearch/orama/issues/851)).

## 6. PGlite with pgvector and pg_textsearch

### Bindings and runtimes

Postgres compiled to WASM: "PGlite can be used in both Node/Bun/Deno or the browser" ([PGlite docs](https://pglite.dev/docs/)); `@electric-sql/pglite` 0.5.17, Apache-2.0, 44.6 M weekly downloads ([npm](https://www.npmjs.com/package/@electric-sql/pglite)). Filesystem storage is listed as "available in Node and Bun", and in-memory storage on all platforms ([API docs](https://pglite.dev/docs/api)). "PGlite only has a single exclusive connection to the database" ([PGlite docs](https://pglite.dev/docs/)), which fits a single-user tool. No native module: **observed**, it ran in memory on Node, Bun and Deno, and reports PostgreSQL 18.7. pgvector and pg_textsearch ship as separate packages, `@electric-sql/pglite-pgvector` and `@electric-sql/pglite-pg_textsearch` ([extensions](https://pglite.dev/extensions/)); **observed** versions 0.8.7 and 1.5.1. (Passing the extensions as the second constructor argument with `undefined` as the first made `CREATE EXTENSION` fail; passing one options object worked.)

### Search

- **Keyword:** pg_textsearch, by Timescale under the PostgreSQL licence, adds a `bm25` index and the `<@>` operator, which "returns negative BM25 scores"; standalone scoring "still uses corpus statistics from the selected BM25 index" ([pg_textsearch README](https://github.com/timescale/pg_textsearch)). Its latest release is v1.5.1 (2026-10-02). **Observed:** rows that do not match score 0 and still come back from `ORDER BY ... LIMIT`, so the keyword leg needs a `< 0` condition.
- **Vector:** pgvector, exact or with HNSW/IVFFlat indexes.
- **Fusion:** none built in; RRF in SQL.
- **Date filter:** for BM25, "PostgreSQL can use a separate index to pre-filter rows before standalone scoring", while with the ordered BM25 index scan other conditions are post-filters, and the scan grows its batch "until the `LIMIT` is filled" ([pg_textsearch README](https://github.com/timescale/pg_textsearch)). For vectors, "With approximate indexes, filtering is applied *after* the index is scanned"; since 0.8.0, `SET hnsw.iterative_scan = strict_order` scans further until enough rows are found ([pgvector README](https://github.com/pgvector/pgvector#filtering)). An exact scan with `WHERE` is exact.

### Shipping and size

A Postgres data directory, or `dumpDataDir()`, which writes a gzipped tarball that `loadDataDir` reads back; "The datadir dump may not be compatible with other Postgres versions; it is only designed for importing back into PGlite" ([API docs](https://pglite.dev/docs/api)). **Observed** at 50k × 384: a 404 MB data directory, a 246.9 MB gzipped dump.

## 7. Filtering by date with vector search

| Store | Exact vector scan + date filter | ANN index + date filter |
|---|---|---|
| SQLite + sqlite-vec | metadata column applied during the scan: k rows, exact | ANN only in 0.1.10 alphas |
| libSQL | `WHERE` on the scan: exact | `vector_top_k` then join: post-filter; **observed** 9 of 20 rows at 50 % visible, 1 of 20 at 5 % |
| DuckDB | `WHERE` on the scan: exact | vss HNSW: pre-filter by default since duckdb-vss#89 (merged 2026-09-14); **observed** 20 of 20 rows at 0.1 % visible on DuckDB 2.0.0 |
| LanceDB | flat search with the default pre-filter: exact | pre-filter by default; ANN recall caveats |
| Orama | candidate set from `where`: exact | no ANN index |
| PGlite + pgvector | `WHERE` on the scan: exact | HNSW post-filters; iterative scans since 0.8.0 |

Replaying history under a cutoff is the hard case for post-filtering: the visible fraction of the corpus goes from close to zero for the first issues to almost all of it for the last ones, and "If a condition matches 10% of rows, with HNSW and the default `hnsw.ef_search` of 40, only 4 rows will match on average" ([pgvector README](https://github.com/pgvector/pgvector#filtering)). At tens of thousands of pieces an exact scan avoids the question: **observed**, every exact-scan hybrid query above took 8–240 ms. Raw float32 vectors take N × D × 4 bytes: at 50k pieces, 77 MB at 384 dimensions, 154 MB at 768, 205 MB at 1,024 and 307 MB at 1,536. Smaller types exist in some stores: int8 and binary in sqlite-vec ([repo](https://github.com/asg017/sqlite-vec)), 16-bit, 8-bit and 1-bit in libSQL ([vector docs](https://docs.turso.tech/features/ai-and-embeddings)), binary in LanceDB ([vector search docs](https://docs.lancedb.com/search/vector-search)), `halfvec` and `bit` in pgvector ([README](https://github.com/pgvector/pgvector)); DuckDB's vss supports only 32-bit floats.

## 8. BM25 under a cutoff

In FTS5, "_N_ is the total number of rows in the FTS5 table and _n(qi)_ is the total number of rows that contain at least one instance of phrase _i_", and "_avgdl_ is the average number of tokens in all documents within the FTS5 table" ([FTS5 § 5.1.1](https://www.sqlite.org/fts5.html)); the `xRowCount` API "provides the total number of rows in the table, not the number that match the current query". pg_textsearch scores with "corpus statistics from the selected BM25 index" ([README](https://github.com/timescale/pg_textsearch)). DuckDB, LanceDB and Orama also keep one index per table; I did not find an option in any of them to compute BM25 statistics over a filtered subset. Under a cutoff, then, the date filter removes future documents from the results but not from the IDF and length normalisation of the scores. Whether that leak matters for the eval, and whether to rebuild keyword indexes per time slice, is not answered here.

## 9. Local checks

All in a scratch directory outside the repo, on Linux x64 (WSL2), with Node 24.16.0, Bun 1.4.5 and Deno 2.9.6 installed from npm. Packages: `better-sqlite3` 13.2.0, `sqlite-vec` 0.1.9, `@libsql/client` 0.18.0, `@duckdb/node-api` 2.0.0-r.1 (DuckDB 2.0.0), `@lancedb/lancedb` 0.41.0, `@orama/orama` and `@orama/plugin-data-persistence` 3.1.18, `@electric-sql/pglite` 0.5.17 with `pglite-pgvector` 0.0.18 and `pglite-pg_textsearch` 0.0.19, `@tursodatabase/database` 0.8.4.

- **Correctness check, every option on every runtime:** six hand-written issues with 4-dimensional vectors, one query ("large file crash") and a cutoff that excludes the newest crash report. Every combination returned the two older crash reports on top and never the excluded one. Deno ran with `-A` from a directory with `package.json` and `node_modules`. The Orama persistence plugin did not import under Deno in that setup (`Import "dpack" not a dependency`); I did not investigate further.
- **Scale check:** 50,000 synthetic pieces; title of 8 words and body of 170 words drawn from an 8,000-word made-up vocabulary with a skewed distribution (about 1.25 KB of text each); random unit vectors of 384 float32 dimensions; dates spread evenly over 2015–2026. Query: the first four words of a late piece and its vector plus noise, with two cutoffs leaving 50 % and 5 % of the corpus visible; k = 20; RRF with k = 60 in SQL. Synthetic text makes the keyword index size only indicative, and random vectors are a worst case for ANN recall. Timings are single runs on that machine, with other work running.
- **Turso Database** (`@tursodatabase/database` 0.8.4, the Rust rewrite, "not yet reached 1.0", full-text search "powered by the awesome tantivy library" and marked experimental, approximate vector indexing on the roadmap ([repo](https://github.com/tursodatabase/turso))): **observed**, it loads on Node and runs exact `vector_distance_cos` queries with a `WHERE`, but has no FTS5 module, and its full-text index requires an experimental flag. Not covered further.
