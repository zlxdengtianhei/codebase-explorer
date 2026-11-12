# Generator Naming Helpers

**Capability.** Builds model-name mappings, acts_as declarations, namespace files, and Rails naming or table helpers for generators.

Observed units show shared generator helper logic used by install, upgrade, and chat UI generators. They include name derivation, association parameters, and namespace module creation.

**Depended on by.**

- [Chat UI Generator](chat-ui-generator.md) · graph-confirmed · 3 edge(s) · Chat UI generator uses generator naming helpers to derive model names, namespaces, and routes.
- [RubyLLM Install Generator](rubyllm-install-generator.md) · graph-confirmed · 1 edge(s)
- [Upgrade Migration Generators](upgrade-migration-generators.md) · graph-confirmed · 4 edge(s) · Upgrade migration generators use generator naming helpers for migration naming and model mappings.
- [V1.7 Upgrade Generator](v1-7-upgrade-generator.md) · graph-confirmed · 4 edge(s)

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (6)

<a id="u-722ba7008886"></a>
### `generator_helpers.rb-acts-as-declarations`

`def acts_as_chat_declaration` · [lib/generators/ruby_llm/generator_helpers.rb:L52-L61][f1]

Builds acts_as declaration strings for chat, message, model, and tool-call models by collecting association parameters.

Chat adds plural messages and model; message adds chat, plural tool calls, and model; model adds plural chats; tool call adds message. Each returns the bare declaration when no parameters are needed, otherwise appends comma-separated parameters.

<a id="u-6592739b9466"></a>
### `generator_helpers.rb-database-capability-checks`

`def postgresql?` · [lib/generators/ruby_llm/generator_helpers.rb:L124-L128][f1]

Checks database adapter and table availability, returning false on any standard error.

PostgreSQL and MySQL checks downcase the adapter name and test for the respective substring; table existence delegates to the connection and also falls back to false on error.

<a id="u-845222358685"></a>
### `generator_helpers.rb-model-mapping-accessors`

`def parse_model_mappings` · [lib/generators/ruby_llm/generator_helpers.rb:L7-L23][f1]

Builds and exposes model-name mappings for chat, message, tool call, and model, with lazy accessors for derived names.

Defaults are Chat, Message, ToolCall, and Model; each mapping containing a colon overrides the key with a classified value, and malformed mappings without a colon are ignored. Generated accessors return model name, table name, variable name, controller class, job class, and partial path; job class camelizes the variable and appends ResponseJob, and parsing happens on first use.

<a id="u-d8b136f4cd9a"></a>
### `generator_helpers.rb-name-conversion-helpers`

`def table_name_for(model_name)` · [lib/generators/ruby_llm/generator_helpers.rb:L163-L165][f1]

Converts model names into table, variable, controller, and partial names for Rails generators.

Table names underscore and pluralize then replace slashes with underscores; variable names underscore and replace slashes; controller names use namespace::PluralController for namespaced models and PluralController otherwise; partial paths combine underscored pluralized path with demodulized underscored name.

<a id="u-83dfe3b53c52"></a>
### `add_association_params`

`def add_association_params(params, default_assoc, table_name, model_name, owner_table…` · [lib/generators/ruby_llm/generator_helpers.rb:L144-L159][f1]

Appends association override parameters for generated acts_as declarations, deriving association name, class name, and foreign key.

The association name is the table symbol when plural is true, otherwise the singularized table symbol. The foreign-key branch uses the owner table's singular id when plural is true or the default association name is already plural; otherwise it uses the associated table's singular id, so a singular has_one takes the else branch. It appends an association override only when the derived association differs from the default, a class override only when the model name differs from the classified association, and a foreign-key override only when it differs from the default association id.

<a id="u-01ee1710a2b8"></a>
### `create_namespace_modules`

`def create_namespace_modules` · [lib/generators/ruby_llm/generator_helpers.rb:L94-L118][f1]

Creates missing namespace module files for namespaced model names, adding a table-name prefix method.

It scans chat, message, tool-call, and model names, collects unique first namespace segments, skips files already present under the Rails root, and writes one module file per missing namespace.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/generator_helpers.rb
