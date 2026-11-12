# V1.7 Upgrade Generator

**Capability.** Upgrades existing Rails apps to the v1.7 acts_as API by updating models, initializer, and migrations.

Observed units show model and initializer updates, migration creation, and success guidance. Use this module for the v1.7 upgrade generator.

**Depends on.**

- [Generator Naming Helpers](generator-naming-helpers.md) · graph-confirmed · 4 edge(s)

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (7)

<a id="u-1530b8d55a46"></a>
### `upgrade_to_v1_7_generator.rb-upgrade-generator-setup`

`def self.source_paths` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L18-L23][f1]

Provides class-level setup for the v1.7 upgrade generator: source paths include own and install templates, and migration numbering delegates to ActiveRecord.

Neither method branches.

<a id="u-d79eb0dcc108"></a>
### `upgrade_to_v1_7_generator.rb-v1-7-upgrade-generator`

`class UpgradeToV17Generator < Rails::Generators::Base` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L10-L18][f1]

Rails generator that prepares an existing app for the v1.7 Rails-like API.

It includes migration and shared generator helpers, exposes model mappings, adds install templates to its source paths, and delegates migration/model/initializer updates and reporting to its steps.

<a id="u-6a0368b1452b"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.create_model_file`

`def create_model_file` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L57-L61][f1]

Creates namespace modules and writes the model model file from a template.

It uses the configured model name for the output path and has no conditional branches.

<a id="u-3222588c4cfe"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.show_next_steps`

`def show_next_steps` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L90-L109][f1]

Prints v1.7 upgrade success and next-step instructions, including migration review, database migration, API changes, a configuration warning, and a guide link.

It has no branching and only reports.

<a id="u-d0231201f8a2"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.update_existing_models`

`def update_existing_models` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L63-L67][f1]

Updates existing chat, message, and tool-call model files to the new acts_as declarations.

It calls the private update helper for each model with its old and new declaration; missing files or files without the old declaration are left unchanged by that helper.

<a id="u-d7533eb92012"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.update_initializer`

`def update_initializer` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L69-L88][f1]

Ensures the RubyLLM initializer enables the new acts_as API.

If the initializer is missing, it warns and writes the initializer template; if it already contains the new-API setting, it returns; otherwise it injects the setting before a line matching end, adding a model-registry class only when the model name is not Model.

<a id="u-5a13244d29dc"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.update_model_acts_as`

`def update_model_acts_as(model_name, old_acts_as, new_acts_as)` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L113-L121][f1]

Replaces an old acts_as declaration in an existing model file with the new declaration.

It returns without change when the model file is missing or does not contain the old declaration at line start; otherwise it substitutes the matching line.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb
