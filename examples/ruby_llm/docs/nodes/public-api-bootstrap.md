# Public API, Bootstrap & Core Runtime

**Capability.** Bootstraps the gem (dependencies, Zeitwerk autoloading, provider registration), exposes the RubyLLM module facade delegating to Chat, Image, Models and other components, and owns shared configuration, per-call isolated contexts, and the base error hierarchy.

Read this first to see how the library is assembled and which entry points exist. RubyLLM.context creates an isolated configuration copy; RubyLLM::Error is the base error type that provider HTTP failures are mapped into. Nothing here talks to a specific provider.

**Depends on.**

- [Conversation Core](conversation-core.md) · model-inferred · 0 edge(s)
- [Model Registry](model-registry.md) · model-inferred · 0 edge(s)
- [Shared Utilities](shared-utilities.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Conversation Core](conversation-core.md) · model-inferred · 0 edge(s)
- [RubyLLM](ruby-llm.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` ruby-llm ` → ` public-api-bootstrap `)
- [HTTP Transport & Provider Base](transport.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
