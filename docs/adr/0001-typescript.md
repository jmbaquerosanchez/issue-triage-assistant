# TypeScript as the language of the product

The product is written in TypeScript, even though most AI tooling is Python-first. Most code here is written by agents and every change is reviewed by a human before it merges, so what matters most is how easily that human reads and checks the code, and they read TypeScript more fluently. Strict static typing also gives agents fast feedback on their own mistakes, and one language covers everything from the MCP server, whose reference SDK is TypeScript, to the user interface.

## Considered Options

- **Python**: a richer ecosystem for local embedding and reranking models, statistics and notebooks. Rejected for the product because what it needs from that ecosystem at run time is available from TypeScript too, and the statistics behind the eval margins are a few lines in any language. What still needs Python, such as checking a model's ONNX build against its reference model or fine-tuning an embedder, runs offline (see Consequences).

## Consequences

- Types are erased at runtime: data entering from outside (GitHub API responses, model outputs) is validated at the boundary, so its types hold.
- Python is allowed only offline, beside the product, in scripts that produce a file: checking a model's ONNX build against its reference, fine-tuning an embedder, running another project's Python code to compare against it, analysing exported results. Nothing the product runs (the CLI, the MCP server, the eval, the demo) imports or launches Python, so nobody needs Python to use or evaluate it.
- The file is the contract between the two: it has a documented format, records which script and inputs produced it, and is validated when TypeScript reads it, like any other outside data.
- These scripts live in `offline/` as one uv project, and CI does not run them. Throwaway scripts behind a research report are evidence of that report, not part of the product, and stay with it in `docs/research/<report>/scripts/`.
