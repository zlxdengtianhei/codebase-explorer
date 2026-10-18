# Shared Utilities

**Capability.** Module-function data helpers (conversion, symbolization, time/date coercion) consumed across the whole library, owning no domain policy.

Treat this as a leaf dependency of most other subtrees; it only normalizes data shapes. Consumers include tool schema building, Model::Info construction, Gemini schema conversion, and legacy persistence.

**Depended on by.**

- [ActiveRecord & Rails Integration](active-record-integration.md) · model-inferred · 0 edge(s)
- [Conversation Core](conversation-core.md) · model-inferred · 0 edge(s)
- [Model Registry](model-registry.md) · model-inferred · 0 edge(s)
- [Provider Adapters](provider-framework.md) · model-inferred · 0 edge(s)
- [Public API, Bootstrap & Core Runtime](public-api-bootstrap.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
