# v1.7 Upgrade Generator

**Capability.** Migrates pre-1.7 apps to the acts_as API: creates migrations, updates the initializer, and rewrites model declarations using GeneratorHelpers.

Read to see what a pre-1.7 app must change; migration creation is conditional on the models table.

**Depends on.**

- [acts\_as Declarations](r2-acts-as-declarations.md) · model-inferred · 0 edge(s)
- [GeneratorHelpers](r2-generator-helpers.md) · graph-confirmed · 9 edge(s) · The v1.7 upgrade generator renders acts_as declarations via GeneratorHelpers.

Parent: [Rails Generators](r2-generators.md)

## Units (3)

<a id="u-2ee28acea205"></a>
### `UpgradeToV17Generator`

`class UpgradeToV17Generator < Rails::Generators::Base` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L10-L18][f1]

Upgrade generator migrating pre-1.7 apps to the acts_as API.

Includes Rails::Generators::Migration and GeneratorHelpers, namespace ruby_llm:upgrade_to_v1_7. Its class-level source_paths override returns both its own templates dir and ../install/templates, so install templates are resolvable. Like the install generator, next_migration_number delegates to ActiveRecord::Generators::Base. Folded steps: create_model_file calls create_namespace_modules then templates model_model.rb.tt to app/models/<model underscore>.rb; update_existing_models calls the private update_model_acts_as for chat, message, and tool_call names with their old macro names and the freshly computed acts_as_* declarations; show_next_steps prints success plus instructions, including a warning fix (config.use_new_acts_as in config/application.rb) if 'undefined method acts_as_model' occurs during migration. The private update_model_acts_as returns unless app/models/<name>.rb exists under Rails.root and its content matches /^\s*<old_acts_as>/; only then it gsub_file-replaces the whole old macro line with the new indented declaration, so models without the old macro are untouched.

calls: [create_namespace_modules](r2-generator-helpers.md#u-01ee1710a2b8), [generator_helpers-acts-as-declarations](r2-generator-helpers.md#u-87f219d97f09)

<a id="u-01c3b06d7d91"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.create_migration_file`

`def create_migration_file` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L34-L55][f1]

Creates the v1.7 migration set, conditional on the models table.

It memoizes @model_table_already_existed from table_exists?(table_name_for(model_model_name)); when false it first templates create_models_migration.rb.tt for the model table (with migration_version and model_model_name locals), sleeps 1 second for a distinct timestamp. It then always templates migration.rb.tt to db/migrate/migrate_to_ruby_llm_model_references.rb, passing migration_version, all four model names, and model_table_already_existed so the migration can skip model-table creation logic when the table already exists.

<a id="u-d7533eb92012"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.update_initializer`

`def update_initializer` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L69-L88][f1]

Ensures config/initializers/ruby_llm.rb enables the new acts_as API.

If the file does not exist it warns via say_status and templates initializer.rb.tt, then returns. Otherwise it reads the file and returns unchanged if it already contains 'config.use_new_acts_as'. Otherwise it injects before the first /^end/ a comment line, 'config.use_new_acts_as = true', and — only when model_model_name differs from 'Model' — a config.model_registry_class line set to the custom model class name, joined with newlines. Insertion targets the first line matching /^end/, assuming the initializer's closing end.

**Uncertainties.**

- Injecting before the first /^end/ assumes the first end closes the configure block; a nested earlier end would misplace the setting.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb