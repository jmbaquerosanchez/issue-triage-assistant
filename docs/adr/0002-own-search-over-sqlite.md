# Keyword scoring and vector scan written in the product, over plain SQLite

Duplicate search does its own BM25 scoring and its own exact vector scan in TypeScript, over plain tables in SQLite through `node:sqlite`. It does not use the search built into a store: not FTS5's `bm25()`, not sqlite-vec, and not LanceDB's built-in hybrid search. Every store computes BM25 statistics (document count, document frequency and average length) over the whole table. A replay would then score with statistics that count later issues, which is a leak, and the lenient replay needs exactly those whole-window statistics to measure that leak. Our scorer takes the instant the statistics are computed at: the cutoff in a replay, the end of the window in the lenient replay, now outside a replay. Pieces are numbered in date order, so everything before a cutoff is a prefix: of each term's posting list for BM25, and of the vector array for the scan. On 350k pieces of 384 dimensions, scanning that prefix took 141 ms with everything visible and 7 ms with 5% visible, against 214 ms and 105 ms for sqlite-vec ([facts](../research/2026-11-21-retrieval-stack-facts/README.md)).

## Considered Options

- **The store's own BM25 (FTS5, LanceDB, DuckDB, pg_textsearch)**: rejected, because its statistics see the future and none computes them over a filtered subset ([stores report](../research/2026-11-20-hybrid-search-stores.md)).
- **A chronological replay that grows the index up to each cutoff**: native BM25 becomes exact and nothing can leak. Rejected because the lenient replay still needs a full index with a date filter, a single eval case needs replaying history up to its cutoff, and the cutoff stops being a parameter of duplicate search's single entry point.
- **A keyword index per quarter**: rejected, because each case either loses the last weeks before its cutoff as candidates or sees up to three months of the future.
- **sqlite-vec for vectors**: rejected. It is pre-v1, had no commits in the six months before this decision, and an early cutoff cuts its cost far less than in proportion.
- **LanceDB, DuckDB, PGlite, Orama, libSQL**: rejected, because once search is our own they bring nothing SQLite lacks. Besides: LanceDB is a directory and pulls Transformers.js 3.0.2 and `openai` as optional dependencies; DuckDB downloads its extensions at run time; PGlite was the slowest; Orama could not persist 50k pieces; libSQL brings its own native binary and an older SQLite, with new work moving to Turso.

## Consequences

- We write and maintain BM25 and its tokenizer. Owning the tokenizer also lets the anchor imitate triage-bench's tokenization.
- Vectors are scanned in int8 in memory to keep the 200 best candidates, which are then reordered with float32 vectors read from the same file. Memory stays a quarter of float32's at any number of pieces.
- The only native dependency the store needs is Node itself, so `engines` is `>=24.15`: from 24.15.0, `node:sqlite` is a release candidate and prints no experimental warning.
