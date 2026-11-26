# Every index is an immutable file, and the surfaces read only the index

An index (the pieces, their posting lists, their vectors, and the facts of each issue that the output shows) is a file written once and never changed, in one format for the live index, the eval's indexes, the demo index and the fixture index. Each ingestion writes a new live index, a generation, and a small `state.db` names the current one: a reader checks it on each call and opens the new file when it changed. The CLI and the MCP server read only the index, never the history. We chose it because the demo index has no history and the eval's indexes are files of their own anyway, so with one format a demo index is an ordinary live index; because nothing is ever renamed over a file a reader holds, which Windows refuses, since SQLite opens its files without `FILE_SHARE_DELETE`; and because a reader never sees an index half built.

## Considered Options

- **One `repository.db` per repository, with the history and the live index, rebuilt inside a WAL transaction**: one file, as the data model was first described. Rejected: a 1–2 GB transaction per daily ingestion, a file kept at about twice the index by free pages, a demo index installed by copying its tables, and a live index in a format other than the eval's and the demo's.
- **Indexes that read their vectors from the vector cache by text hash**: nothing duplicated for the live index. Rejected: the eval's and the demo index files would still need a partial copy of the cache, in another module's schema, and every MCP server would read 350k vectors by hash at start and at every new generation.
- **Surfaces that read facts and text from the history**: rejected, since a demo index has no history and would need a facts table of its own.

## Consequences

- Per target repository: `history.db`, written only by an ingestion holding the lock; `vectors.db`, the vector cache; `index-<generation>.db`; and `state.db`. Each has one owning module.
- An index carries its vectors, copied from the cache when it is built. In godot that is about 0.15 GB more per live index without comment pieces and 0.7 GB with them, and the disk holds two live indexes during a rebuild.
- An old generation is deleted once no process holds it; a deletion that fails is retried at the next ingestion.
- The live index rejects any cutoff, so an `as_of` on `find_duplicates` would mean serving a full index instead.
- `demo` refuses to install over a real ingestion, and a first real ingestion replaces an installed demo index when it completes.
