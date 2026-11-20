# TypeScript as the language of the codebase

The codebase is written in TypeScript, even though most AI tooling is Python-first. Most code here is written by agents and every change is reviewed by a human before it merges, so what matters most is how easily that human reads and checks the code, and they read TypeScript more fluently. Strict static typing also gives agents fast feedback on their own mistakes, and one language covers everything from the MCP server, whose reference SDK is TypeScript, to the user interface.

## Considered Options

- **Python**: a richer ecosystem for local embedding and reranking models, statistics and notebooks. Rejected because what this project needs from that ecosystem is available from TypeScript too, and the statistics behind the eval margins are a few lines in any language.

## Consequences

- Types are erased at runtime: data entering from outside (GitHub API responses, model outputs) is validated at the boundary, so its types hold.
