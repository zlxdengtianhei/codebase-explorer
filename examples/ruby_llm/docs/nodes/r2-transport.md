# HTTP Transport and Provider Base

**Capability.** Owns the shared request pipeline: Faraday connection setup with logging/retries/error mapping, the abstract Provider base with its registry, and provider-agnostic streaming over SSE.

Use this subtree to understand how any provider issues and streams HTTP requests. Concrete providers only supply URLs, payloads, and parsers on top of these layers.

**Children.**

- [Provider Connection](r2-connection.md) `r2-connection` · 1 unit(s)
- [Provider Base and Registry](r2-provider-base.md) `r2-provider-base` · 2 unit(s)
- [Shared Streaming](r2-streaming-shared.md) `r2-streaming-shared` · 4 unit(s)

Parent: [RubyLLM](r2-ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
