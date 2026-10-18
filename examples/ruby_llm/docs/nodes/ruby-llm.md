# RubyLLM

**Capability.** A unified Ruby interface to multiple LLM providers: it rolls up bootstrapping and configuration, shared utilities, conversation machinery, model metadata, HTTP transport, per-provider adapters, ActiveRecord persistence, and developer tooling under one module facade.

Start here to navigate the gem. The root only aggregates; each child owns one concern. Provider-independent concepts live in conversation-core and model-registry, provider-specific behavior under provider-framework, and cross-cutting infrastructure under shared-utilities and transport.

**Children.**

- [RubyLLM Gem](r1-ruby-llm-gem.md) `r1-ruby-llm-gem` · 0 unit(s)
- [RubyLLM](r2-ruby-llm.md) `r2-ruby-llm` · 0 unit(s)
- [Public API, Bootstrap & Core Runtime](public-api-bootstrap.md) `public-api-bootstrap` · 0 unit(s)
- [Shared Utilities](shared-utilities.md) `shared-utilities` · 0 unit(s)
- [Conversation Core](conversation-core.md) `conversation-core` · 0 unit(s)
- [Model Registry](model-registry.md) `model-registry` · 0 unit(s)
- [HTTP Transport & Provider Base](transport.md) `transport` · 0 unit(s)
- [Provider Adapters](provider-framework.md) `provider-framework` · 0 unit(s)
- [ActiveRecord & Rails Integration](active-record-integration.md) `active-record-integration` · 0 unit(s)
- [Developer Tooling](developer-tooling.md) `developer-tooling` · 0 unit(s)

**Depends on.**

- [Public API, Bootstrap & Core Runtime](public-api-bootstrap.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` ruby-llm ` → ` public-api-bootstrap `)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
