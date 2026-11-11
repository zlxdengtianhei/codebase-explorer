# Generator shared helpers

**Capability.** Provides helpers mixed into all RubyLLM Rails generators: model-mapping parsing, naming and table derivation, acts_as declaration builders, and namespace module creation.

Shared plumbing for the Rails generators: parsing 'key:Value' model mappings, deriving table/variable/controller names per model type, building acts_as declaration strings, and creating namespace module files. Every generator depends on this for consistent naming.

**Depended on by.**

- [Chat UI scaffolding generator](chat-ui-scaffolding-generator.md) · graph-confirmed · 3 edge(s) · The chat UI generator uses shared helpers for naming, model mappings, and acts_as declarations.
- [Install generator](install-generator.md) · graph-confirmed · 1 edge(s)
- [Migration numbering and v1.9](migration-numbering-and-v1-9.md) · graph-confirmed · 2 edge(s)
- [v1.7 upgrade generator](v1-7-upgrade-generator.md) · graph-confirmed · 4 edge(s)

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (10)

<a id="u-1da9cc72727c"></a>
### `generator_helpers.rb-acts-as-declaration-builders`

`def acts_as_chat_declaration` · [lib/generators/ruby_llm/generator_helpers.rb:L52-L61][f1]

Each builds a Ruby declaration string for a model: acts_as_chat (message and model associations), acts_as_message (chat, tool_calls, model), acts_as_model (chats), acts_as_tool_call (message).

They collect association parameters via add_association_params and append them space-joined only when any are produced, yielding e.g. 'acts_as_chat messages: :llm_messages, ...' or a bare 'acts_as_chat'.

<a id="u-a79a5bf15ff3"></a>
### `generator_helpers.rb-database-introspection-helpers`

`def postgresql?` · [lib/generators/ruby_llm/generator_helpers.rb:L124-L128][f1]

postgresql?

and mysql? check the ActiveRecord adapter name (downcased) for 'postgresql'/'mysql'; table_exists? delegates to connection.table_exists?. All three rescue StandardError and return false, so a missing connection or unloaded schema degrades to a negative answer rather than raising.

<a id="u-d8b136f4cd9a"></a>
### `generator_helpers.rb-name-conversion-helpers`

`def table_name_for(model_name)` · [lib/generators/ruby_llm/generator_helpers.rb:L163-L165][f1]

table_name_for converts a model name to a table name with slashes replaced by underscores ('Assistant::Chat' → 'assistant_chats'); variable_name_for yields the underscored instance-variable-style name ('LLM::Chat' → 'llm_chat'); controller_class_name_for returns 'Namespace::PluralController' for namespaced names or 'PluralController' otherwise; partial_path_for returns 'pluralized_underscored_path/demodulized_underscored_name'.

<a id="u-83dfe3b53c52"></a>
### `add_association_params`

`def add_association_params(params, default_assoc, table_name, model_name, owner_table…` · [lib/generators/ruby_llm/generator_helpers.rb:L144-L159][f1]

Appends association parameters only where they deviate from Rails defaults.

It adds '<assoc>: :<name>' when the derived association symbol differs from the default, '<singular_assoc>_class' when the model name differs from the classified association, and '<assoc>_foreign_key' when the computed key differs from <default_assoc>_id. Foreign keys are computed as owner_table.singularize + '_id' for has_many/has_one (plural flag or pluralized default assoc) and table_name.singularize + '_id' for belongs_to.

<a id="u-01ee1710a2b8"></a>
### `create_namespace_modules`

`def create_namespace_modules` · [lib/generators/ruby_llm/generator_helpers.rb:L94-L118][f1]

Creates app/models/<namespace>.rb module files for each distinct first-level namespace found among the four model names, skipping any whose file already exists.

Each generated module defines self.table_name_prefix returning the underscored namespace plus underscore, matching Rails table-naming conventions.

<a id="u-cb042d8ec59c"></a>
### `migration_version`

`def migration_version` · [lib/generators/ruby_llm/generator_helpers.rb:L120-L122][f1]

Returns the Rails-version bracket string like '[7.1]' for migration template versioning.

<a id="u-5c99c008abdc"></a>
### `parse_model_mappings`

`def parse_model_mappings` · [lib/generators/ruby_llm/generator_helpers.rb:L7-L23][f1]

Builds and memoizes @model_names, defaulting chat/message/tool_call/model to Chat/Message/ToolCall/Model, then overrides entries from each 'key:Value' mapping argument (split on the first colon, value classified).

Returns the hash; mappings without a colon are ignored.

<a id="u-32cdf17fa86f"></a>
### `GeneratorHelpers`

`module GeneratorHelpers` · [lib/generators/ruby_llm/generator_helpers.rb:L6-L7][f1]

Module of shared helpers mixed into all RubyLLM generators; it provides model-mapping parsing, dynamically defined per-type accessors, acts_as declaration builders, namespace module creation, and name-conversion utilities.

<a id="u-1981791de1fa"></a>
### `lib/generators/ruby_llm/generator_helpers.rb:GeneratorHelpers`

`module GeneratorHelpers` · [lib/generators/ruby_llm/generator_helpers.rb:L23-L52][f1]

For each of chat, message, tool_call, and model, defines six accessors: <type>_model_name (memoized parse of mappings), <type>_table_name, <type>_variable_name, <type>_controller_class_name, <type>_job_class_name (variable name camelized plus 'ResponseJob'), and <type>_partial, each delegating to the corresponding conversion helper.

<a id="u-01c3b06d7d91"></a>
### `RubyLLM.Generators.UpgradeToV17Generator.create_migration_file`

`def create_migration_file` · [lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb:L34-L55][f2]

Records whether the models table already exists (table_exists?

on the mapped model table). If it does not, it first templates create_models_migration with version and model name, sleeping one second for a distinct timestamp; then always templates the migrate_to_ruby_llm_model_references migration, passing all model names and the model_table_already_existed flag as template locals.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/generator_helpers.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/upgrade_to_v1_7/upgrade_to_v1_7_generator.rb
