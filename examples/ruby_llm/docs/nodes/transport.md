# HTTP Transport & Provider Base

**Capability.** Owns the shared request pipeline: Faraday connection setup with logging, retries, and error mapping; the abstract Provider base with its registry; and provider-agnostic SSE streaming.

Use this to understand how any provider issues and streams HTTP requests. Concrete providers only supply URLs, payloads, and parsers on top of these layers.

**Depends on.**

- [Public API, Bootstrap & Core Runtime](public-api-bootstrap.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Provider Adapters](provider-framework.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
