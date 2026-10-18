# RubyLLM

**Capability.** A unified Ruby interface to LLM providers: configuration, provider adapters, streaming, ActiveRecord persistence, generators, and maintenance tasks.

Start here to navigate the codebase. The tree splits into shared runtime infrastructure, per-provider adapters, an ActiveRecord integration layer, Rails generators, and rake tooling.

**Children.**

- [Core Runtime](r2-core-runtime.md) `r2-core-runtime` · 0 unit(s)
- [HTTP Transport and Provider Base](r2-transport.md) `r2-transport` · 0 unit(s)
- [Provider Adapters](r2-providers.md) `r2-providers` · 0 unit(s)
- [ActiveRecord Integration](r2-active-record-integration.md) `r2-active-record-integration` · 0 unit(s)
- [Rails Generators](r2-generators.md) `r2-generators` · 0 unit(s)
- [Rake Tasks](r2-rake-tasks.md) `r2-rake-tasks` · 9 unit(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
