# Upgrade Migration Generators

**Capability.** Creates v1.7 and v1.9 upgrade migrations and prints migration guidance for existing apps.

Observed units show upgrade migration generation and migration-version helpers. They include v1.9 message-column migration and v1.7 migration existence checks.

**Depends on.**

- [Generator Naming Helpers](generator-naming-helpers.md) · graph-confirmed · 4 edge(s) · Upgrade migration generators use generator naming helpers for migration naming and model mappings.

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (5)

<a id="u-eea4e1cb7ba1"></a>
### `upgrade_to_v1_9_generator.rb-v1-9-migration-generation`

`def self.next_migration_number(dirname)` · [lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb:L21-L23][f1]

Provides migration numbering and creates the v1.9 message-column migration.

Numbering delegates to the ActiveRecord generator base; migration creation parses model mappings first, then writes the migration template with the migration version and message table name.

<a id="u-4ea6bbbb7632"></a>
### `upgrade_to_v1_9_generator.rb-v1-9-upgrade-generator`

`class UpgradeToV19Generator < Rails::Generators::Base` · [lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb:L10-L21][f1]

Rails generator that adds v1.9 message columns to an existing app.

It includes migration and shared generator helpers, exposes model mappings, and delegates migration creation and next-step reporting to its steps.

<a id="u-cb042d8ec59c"></a>
### `migration_version`

`def migration_version` · [lib/generators/ruby_llm/generator_helpers.rb:L120-L122][f2]

Returns the Rails migration version string from the major and minor Rails version constants.

It has no branching and does not inspect the database.

<a id="u-01c3b06d7d91"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.create_migration_file`

`def create_migration_file` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L34-L55][f3]

Creates the v1.7 upgrade migrations, first checking whether the model table already exists.

If the model table is missing, it creates the models migration and sleeps one second; it then always creates the model-reference migration, passing model names and the pre-existence flag.

<a id="u-69542363efa4"></a>
### `RubyLLM.Generators.UpgradeToV19Generator.show_next_steps`

`def show_next_steps` · [lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb:L34-L46][f1]

Prints v1.9 upgrade success and next-step instructions for reviewing the migration, running database migration, restarting the server, and consulting release notes.

It has no branching and only reports.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_9/upgrade_to_v1_9_generator.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/generator_helpers.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb
