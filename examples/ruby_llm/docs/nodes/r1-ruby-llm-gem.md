# RubyLLM Gem

**Capability.** A unified Ruby interface to multiple LLM providers: conversation handling, model metadata, provider adapters, Rails/ActiveRecord integration, and developer tooling, all surfaced through a single module facade.

Start here to understand the gem's top-level responsibilities. Each subtree owns one concern; the root only rolls them up. Provider-independent core concepts live in conversation-core and model-registry, while provider-specific behavior lives under provider-framework.

**Children.**

- [Public API & Bootstrap](r1-public-api-bootstrap.md) `r1-public-api-bootstrap` · 5 unit(s)
- [Shared Utilities](r1-shared-utilities.md) `r1-shared-utilities` · 1 unit(s)
- [Conversation Core](r1-conversation-core.md) `r1-conversation-core` · 0 unit(s)
- [Model Registry](r1-model-registry.md) `r1-model-registry` · 0 unit(s)
- [ActiveRecord & Rails Integration](r1-active-record-integration.md) `r1-active-record-integration` · 1 unit(s)
- [Provider Framework](r1-provider-framework.md) `r1-provider-framework` · 0 unit(s)
- [Developer Tooling](r1-developer-tooling.md) `r1-developer-tooling` · 0 unit(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
