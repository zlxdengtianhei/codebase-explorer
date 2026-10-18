# Core Runtime

**Capability.** Shared configuration, per-call context, content/value objects, and error handling that all providers and integrations depend on.

Use this subtree to understand how settings flow, how message content and results are represented, and how provider HTTP failures become RubyLLM errors. Nothing here talks to a specific provider.

**Children.**

- [Configuration and Context](r2-config-context.md) `r2-config-context` · 2 unit(s)
- [Content and Result Value Objects](r2-content-value-objects.md) `r2-content-value-objects` · 8 unit(s)
- [Error Hierarchy and Middleware](r2-error-handling.md) `r2-error-handling` · 4 unit(s)

Parent: [RubyLLM](r2-ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
