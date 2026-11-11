# Migration numbering and v1.9

**Capability.** Provides timestamped migration-number delegation for generators and the v1.9 upgrade generator adding cached-token and raw-content message columns.

Two small pieces: a shared next_migration_number hook delegating to ActiveRecord's generator base, and the upgrade_to_v1_9 generator that adds the v1.9 message columns via one migration with follow-up instructions.

**Depends on.**

- [Generator shared helpers](generator-shared-helpers.md) · graph-confirmed · 2 edge(s)

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (4)

<a id="u-01a179fccbbe"></a>
### `install_generator.rb-migration-numbering`

`def self.next_migration_number(dirname)` · [lib/generators/ruby_llm/install/install_generator.rb:L26-L28][f1]

Each generator's class-level next_migration_number delegates to ActiveRecord::Generators::Base.next_migration_number so migration_template can compute timestamped filenames.

<a id="u-fae4771ef469"></a>
### `UpgradeToV19Generator`

`class UpgradeToV19Generator < Rails::Generators::Base` · [lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb:L10-L21][f2]

Rails generator (namespace ruby_llm:upgrade_to_v1_9) that adds the v1.9 message columns (cached tokens and raw content) via a single migration, parameterized by an optional message model mapping; includes Migration and GeneratorHelpers.

<a id="u-612a5f219e72"></a>
### `RubyLLM.Generators.UpgradeToV19Generator.create_migration_file`

`def create_migration_file` · [lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb:L25-L32][f2]

Parses model mappings, then templates add_v1_9_message_columns.rb.tt to db/migrate/add_ruby_llm_v1_9_columns.rb, passing migration_version and the mapped message table name as locals.

<a id="u-69542363efa4"></a>
### `RubyLLM.Generators.UpgradeToV19Generator.show_next_steps`

`def show_next_steps` · [lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb:L34-L46][f2]

Prints success status and next steps: review the migration, run db:migrate, restart the server, and consult the v1.9.0 release notes.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/install/install_generator.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb
