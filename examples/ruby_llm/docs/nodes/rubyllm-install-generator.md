# RubyLLM Install Generator

**Capability.** Installs RubyLLM initializer, models, migrations, and optional ActiveStorage into a Rails app.

Observed units show the install generator flow and generated file paths. They include initializer, migration, model creation, and post-install guidance.

**Depends on.**

- [Generator Naming Helpers](generator-naming-helpers.md) · graph-confirmed · 1 edge(s)

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (7)

<a id="u-8b4f91b3db3d"></a>
### `install_generator.rb-install-generator`

`class InstallGenerator < Rails::Generators::Base` · [lib/generators/ruby_llm/install/install_generator.rb:L10-L26][f1]

Rails generator that installs RubyLLM models, migrations, and initializer, optionally installing ActiveStorage.

It includes migration and shared generator helpers, exposes model mappings and a skip-ActiveStorage option, and delegates file creation and reporting to its steps.

<a id="u-03796e69a149"></a>
### `RubyLLM.Generators.InstallGenerator.create_initializer`

`def create_initializer` · [lib/generators/ruby_llm/install/install_generator.rb:L62-L64][f1]

Writes the RubyLLM initializer template to the Rails initializer path.

It has no branching and writes through the template action.

<a id="u-a350949add3d"></a>
### `RubyLLM.Generators.InstallGenerator.create_migration_files`

`def create_migration_files` · [lib/generators/ruby_llm/install/install_generator.rb:L30-L50][f1]

Creates five migration files for chats, messages, tool calls, models, and reference additions using configured table names.

It sleeps one second between templates to keep timestamps distinct; it has no conditional branches.

<a id="u-b64587d208e0"></a>
### `RubyLLM.Generators.InstallGenerator.create_model_files`

`def create_model_files` · [lib/generators/ruby_llm/install/install_generator.rb:L52-L60][f1]

Creates namespace modules and then writes chat, message, tool-call, and model files from templates.

It uses configured model names for output paths and has no conditional branches.

<a id="u-b68b75f6f310"></a>
### `RubyLLM.Generators.InstallGenerator.install_active_storage`

`def install_active_storage` · [lib/generators/ruby_llm/install/install_generator.rb:L66-L71][f1]

Installs ActiveStorage unless the skip option is set.

When not skipped, it prints a status line and runs the Rails ActiveStorage install command; when skipped, it returns without side effects.

<a id="u-631901cca461"></a>
### `RubyLLM.Generators.InstallGenerator.next_migration_number`

`def self.next_migration_number(dirname)` · [lib/generators/ruby_llm/install/install_generator.rb:L26-L28][f1]

Delegates migration numbering to the ActiveRecord generator base.

It returns that delegated value and has no additional branching.

<a id="u-ac5bf1dcbba4"></a>
### `RubyLLM.Generators.InstallGenerator.show_install_info`

`def show_install_info` · [lib/generators/ruby_llm/install/install_generator.rb:L73-L103][f1]

Prints post-install guidance for RubyLLM, including next steps, model-registry notes, documentation, and ActiveStorage status.

It always prints the main success and next-step text; when ActiveStorage was skipped it adds a warning and manual enablement instructions.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/install/install_generator.rb
