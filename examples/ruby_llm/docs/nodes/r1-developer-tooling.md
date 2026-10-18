# Developer Tooling

**Capability.** Rails generators for install/upgrade migrations and rake tasks that refresh the model registry, generate docs and aliases from live provider data.

Use the generators when adding RubyLLM to an app (models, migrations, initializer, v1.9 columns). Use the models rake tasks to refresh the catalog and regenerate reference documentation and alias data.

**Children.**

- [Rails Generators](r1-generators.md) `r1-generators` · 3 unit(s)
- [Model Maintenance Rake Tasks](r1-model-maintenance-tasks.md) `r1-model-maintenance-tasks` · 18 unit(s)

Parent: [RubyLLM Gem](r1-ruby-llm-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
