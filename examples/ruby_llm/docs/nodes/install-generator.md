# Install generator

**Capability.** Generates the initial RubyLLM Rails setup: five ordered migrations, model files, an initializer, and optional ActiveStorage installation.

The primary install generator: creates chats, messages, tool_calls, models, and add-references migrations (timestamp-spaced), templates the four model classes and initializer, and optionally runs active_storage:install. Ends with next-step guidance.

**Depends on.**

- [Generator shared helpers](generator-shared-helpers.md) · graph-confirmed · 1 edge(s)

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (5)

<a id="u-76516f417b50"></a>
### `install_generator.rb-model-and-initializer-files`

`def create_model_files` · [lib/generators/ruby_llm/install/install_generator.rb:L52-L60][f1]

create_model_files first ensures namespace modules exist, then templates chat, message, tool_call, and model models into app/models using underscored names.

create_initializer templates the RubyLLM initializer to config/initializers/ruby_llm.rb.

<a id="u-276ef705fe3b"></a>
### `InstallGenerator`

`class InstallGenerator < Rails::Generators::Base` · [lib/generators/ruby_llm/install/install_generator.rb:L10-L26][f1]

Rails generator (namespace ruby_llm:install) that creates RubyLLM migrations, model files, an initializer, and optionally installs ActiveStorage, driven by model-mapping arguments and a skip_active_storage option; includes Rails::Generators::Migration and GeneratorHelpers.

<a id="u-a350949add3d"></a>
### `RubyLLM.Generators.InstallGenerator.create_migration_files`

`def create_migration_files` · [lib/generators/ruby_llm/install/install_generator.rb:L30-L50][f1]

Generates five migrations in order: chats, messages, tool_calls, models, then an add-references migration, sleeping one second between each to guarantee distinct timestamp prefixes.

File names embed the mapped table names.

<a id="u-b68b75f6f310"></a>
### `RubyLLM.Generators.InstallGenerator.install_active_storage`

`def install_active_storage` · [lib/generators/ruby_llm/install/install_generator.rb:L66-L71][f1]

Unless the skip_active_storage option is set, announces and runs 'rails active_storage:install' via rails_command to enable file attachments; with the flag set it returns without side effects.

<a id="u-ac5bf1dcbba4"></a>
### `RubyLLM.Generators.InstallGenerator.show_install_info`

`def show_install_info` · [lib/generators/ruby_llm/install/install_generator.rb:L73-L103][f1]

Prints post-install guidance: success banner, ActiveStorage confirmation when not skipped, next steps (db:migrate, API keys, a sample Chat.create!...ask call), database-backed model registry notes, a warning block with remediation steps when ActiveStorage was skipped, and documentation/promotional links.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/install/install_generator.rb
