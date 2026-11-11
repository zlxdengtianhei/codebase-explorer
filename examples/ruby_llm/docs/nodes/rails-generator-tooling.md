# Rails Generator Tooling

**Capability.** Generates migrations, models, initializers, and chat UI scaffolding to install and upgrade RubyLLM in Rails applications.

Come here to install or upgrade the gem in a Rails app. Generator shared helpers support all generators; the remaining children cover installation, the v1.7 and v1.9 upgrades, chat UI scaffolding, and migration numbering.

**Children.**

- [Generator shared helpers](generator-shared-helpers.md) `generator-shared-helpers` · 10 unit(s)
- [v1.7 upgrade generator](v1-7-upgrade-generator.md) `v1-7-upgrade-generator` · 8 unit(s)
- [Chat UI scaffolding generator](chat-ui-scaffolding-generator.md) `chat-ui-scaffolding-generator` · 8 unit(s)
- [Install generator](install-generator.md) `install-generator` · 5 unit(s)
- [Migration numbering and v1.9](migration-numbering-and-v1-9.md) `migration-numbering-and-v1-9` · 4 unit(s)

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
