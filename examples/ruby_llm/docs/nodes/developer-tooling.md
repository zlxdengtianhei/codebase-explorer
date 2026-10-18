# Developer Tooling

**Capability.** Rails generators for install, chat UI, and upgrade migrations built on shared GeneratorHelpers, plus rake tasks for gem release automation, refreshing the model registry from live provider data, regenerating docs/aliases, and re-recording VCR cassettes.

Use the generators when adding RubyLLM to an app (models, migrations, initializer, v1.9 columns); all name logic funnels through GeneratorHelpers. Use the rake tasks to refresh the catalog, regenerate reference documentation, and re-record provider cassettes.

**Depends on.**

- [ActiveRecord & Rails Integration](active-record-integration.md) · model-inferred · 0 edge(s)
- [Model Registry](model-registry.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
