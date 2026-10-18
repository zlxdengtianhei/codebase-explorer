# Rails Generators

**Capability.** Install generator creating models, five timestamped migrations, and initializer; upgrade generator adding v1.9 cached-token and raw-content columns.

Run the install generator for a new app; run the v1.9 upgrade generator on existing installs.

**Depends on.**

- [GeneratorHelpers](r2-generator-helpers.md) · graph-only · 3 edge(s)

Parent: [Developer Tooling](r1-developer-tooling.md)

## Units (3)

<a id="u-276ef705fe3b"></a>
### `InstallGenerator`

`class InstallGenerator < Rails::Generators::Base` · [lib/generators/ruby_llm/install/install_generator.rb:L10-L26][f1]

Install generator creating RubyLLM models, migrations, and initializer.

Includes Rails::Generators::Migration and GeneratorHelpers, namespace ruby_llm:install, source_root templates dir, array argument model_mappings, and boolean class_option :skip_active_storage (default false). Folded steps: self.next_migration_number delegates to ActiveRecord::Generators::Base.next_migration_number for timestamped migrations; create_model_files first calls create_namespace_modules, then templates chat/message/tool_call/model models to app/models/<underscored name>.rb; create_initializer templates initializer.rb.tt to config/initializers/ruby_llm.rb; install_active_storage returns immediately when options[:skip_active_storage] is true, otherwise says a cyan notice and runs rails_command 'active_storage:install'; show_install_info prints success/next-step text, conditionally omitting the ActiveStorage line and instead printing skip instructions (including adding has_many_attached :attachments to the message model) when the skip option is set.

calls: [create_namespace_modules](r2-generator-helpers.md#u-01ee1710a2b8)

<a id="u-a350949add3d"></a>
### `RubyLLM.Generators.InstallGenerator.create_migration_files`

`def create_migration_files` · [lib/generators/ruby_llm/install/install_generator.rb:L30-L50][f1]

Templates five migrations with distinct timestamps.

It emits create_<chat/message/tool_call/model table> migrations from .tt templates, each separated by sleep 1 so consecutive migration timestamps differ by at least a second (timestamps have second resolution). Finally it templates a fifth migration 'add_references_to_<chat>_<tool_call>_and_<message>.rb' fixing references. The sleeps make this step take about four seconds; each migration_template is otherwise an unconditional file creation from the shared template directory.

**Notes.**

- side_effect: Four explicit sleep 1 calls serialize timestamps; removing them could yield duplicate migration timestamps.

<a id="u-fae4771ef469"></a>
### `UpgradeToV19Generator`

`class UpgradeToV19Generator < Rails::Generators::Base` · [lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb:L10-L21][f2]

Upgrade generator adding v1.9 cached-token and raw-content columns to an existing app.

Includes Rails::Generators::Migration and GeneratorHelpers; namespace ruby_llm:upgrade_to_v1_9; array argument model_mappings (banner suggests only message:MessageName). Folded steps: next_migration_number delegates to ActiveRecord::Generators::Base; create_migration_file calls parse_model_mappings (needed because no other step forces parsing) then templates add_v1_9_message_columns.rb.tt to the fixed path db/migrate/add_ruby_llm_v1_9_columns.rb, passing migration_version and message_table_name; show_next_steps prints success plus instructions to review/migrate/restart. All output paths are fixed regardless of mappings; only message_table_name varies.

calls: [parse_model_mappings](r2-generator-helpers.md#u-5c99c008abdc)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/install/install_generator.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb