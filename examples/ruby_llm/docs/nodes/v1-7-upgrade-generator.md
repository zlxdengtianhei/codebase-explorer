# v1.7 upgrade generator

**Capability.** Upgrades pre-1.7 apps to the Rails-like API by generating models migrations, the model class, rewriting acts_as declarations, and ensuring the initializer exists.

A Rails generator that migrates existing RubyLLM installs to the v1.7 API: creates the models migration and model file, rewrites acts_as lines in chat/message/tool_call models, and prints migration and workaround guidance. Reuses install-generator templates via source_paths.

**Depends on.**

- [Generator shared helpers](generator-shared-helpers.md) · graph-confirmed · 4 edge(s)

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (8)

<a id="u-2ee28acea205"></a>
### `UpgradeToV17Generator`

`class UpgradeToV17Generator < Rails::Generators::Base` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L10-L18][f1]

Rails generator (namespace ruby_llm:upgrade_to_v1_7) that upgrades pre-1.7 RubyLLM apps to the Rails-like API by generating a models migration plus a references migration, creating the model class, rewriting acts_as declarations in existing models, and updating the initializer; includes Migration and GeneratorHelpers.

<a id="u-2cfa23c006eb"></a>
### `lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:UpgradeToV17Generator`

`class UpgradeToV17Generator < Rails::Generators::Base` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L23-L30][f1]

Class-body segment of the v1.7 upgrade generator that declares its public invocation surface: the `model_mappings` array argument (default empty, banner 'chat:ChatName message:MessageName ...') and the generator description/usage string.

It carries no executable logic; it only configures how `rails g ruby_llm:upgrade_to_v1_7` parses arguments and what `rails g --help` shows. Behavior of the methods defined inside this region is documented in their own units.

group: [UpgradeToV17Generator](v1-7-upgrade-generator.md#u-2ee28acea205)

**Uncertainties.**

- Exact member-to-region split is inferred from line ranges; whether this region also encloses the class-level next_migration_number cannot be fully confirmed from the excerpt.

<a id="u-6a0368b1452b"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.create_model_file`

`def create_model_file` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L57-L61][f1]

Ensures namespace modules exist, then templates the model model file to app/models/<underscored model name>.rb.

<a id="u-3222588c4cfe"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.show_next_steps`

`def show_next_steps` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L90-L109][f1]

Prints upgrade completion status and next steps: review migrations, run db:migrate, adopt the new API, plus a workaround for 'undefined method acts_as_model' during migration (setting config.use_new_acts_as in config/application.rb) and a link to the migration guide.

<a id="u-8faf734e10d3"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.source_paths`

`def self.source_paths` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L18-L23][f1]

Overrides source_paths to search this generator's templates first, then the install generator's templates, so shared templates like the models migration and model model are reused.

<a id="u-d0231201f8a2"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.update_existing_models`

`def update_existing_models` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L63-L67][f1]

Rewrites the acts_as declaration in each existing chat, message, and tool_call model by delegating to update_model_acts_as with the freshly built declarations from GeneratorHelpers.

<a id="u-d7533eb92012"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.update_initializer`

`def update_initializer` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L69-L88][f1]

Ensures config/initializers/ruby_llm.rb exists, creating it from template with a warning if missing.

If it exists but already mentions 'config.use_new_acts_as', it returns without changes; otherwise it injects 'config.use_new_acts_as = true' (plus config.model_registry_class when the model name is not the default 'Model') before the first end line.

<a id="u-5a13244d29dc"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.update_model_acts_as`

`def update_model_acts_as(model_name, old_acts_as, new_acts_as)` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L113-L121][f1]

For one model, returns silently if its file is missing or its content lacks a line matching ^\s*<old_acts_as>; otherwise gsub-replaces that whole line with the new two-space-indented declaration, leaving other lines untouched.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb
