# GeneratorHelpers

**Capability.** Shared generator utility module: parses model_mappings into derived name accessors, renders acts_as_* declaration strings with non-default options, and creates namespace modules.

Read to understand how generator arguments become class/association names and declaration code reused by all generators.

**Depended on by.**

- [Chat UI Generator](r2-chat-ui-generator.md) · graph-confirmed · 3 edge(s) · The chat UI generator derives names and adapter settings through GeneratorHelpers.
- [v1.7 Upgrade Generator](r2-upgrade-generator.md) · graph-confirmed · 9 edge(s) · The v1.7 upgrade generator renders acts_as declarations via GeneratorHelpers.
- [Rails Generators](r1-generators.md) · graph-only · 3 edge(s)

Parent: [Rails Generators](r2-generators.md)

## Units (6)

<a id="u-5c99c008abdc"></a>
### `parse_model_mappings`

`def parse_model_mappings` · [lib/generators/ruby_llm/generator_helpers.rb:L7-L23][f1]

Parses the generator's model_mappings argument into @model_names, the cached source of all derived names.

It initializes chat/message/tool_call/model to their defaults, then for each mapping containing ':' splits on the first ':' (limit 2) and stores key.to_sym => value.classify. Mappings without ':' are silently ignored. Returns the hash and memoizes it in @model_names; the dynamically defined accessors (see the module group) lazily invoke this, so first access to any *_model_name parses the argument list.

**Uncertainties.**

- The graph shows an ambiguous each resolution (Chat.each/Models.each candidates); the source clearly iterates the model_mappings array.

<a id="u-96b33ea896ef"></a>
### `generator_helpers-derived-accessors`

`module GeneratorHelpers` · [lib/generators/ruby_llm/generator_helpers.rb:L23-L52][f1]

Module regions of GeneratorHelpers enclosing the dynamically generated name accessors.

A %i[chat message tool_call model] loop defines, for each type, six methods: <type>_model_name (lazily calling parse_model_mappings and reading @model_names[type], so any miss returns nil rather than a default), <type>_table_name, <type>_variable_name, <type>_controller_class_name, and <type>_partial (each delegating to the corresponding *_for converter with the model name), and <type>_job_class_name ('<variable_name.camelize>ResponseJob'). These accessors are the interface all four generators use; their output therefore depends entirely on parse_model_mappings having classified mapping values. Regions outside the loop are only module open/close lines.

calls: [parse_model_mappings](r2-generator-helpers.md#u-5c99c008abdc), [generator_helpers-name-and-adapter-helpers](r2-generator-helpers.md#u-47e247bb7cdb)

<a id="u-47e247bb7cdb"></a>
### `generator_helpers-name-and-adapter-helpers`

`def migration_version` · [lib/generators/ruby_llm/generator_helpers.rb:L120-L122][f1]

Small conversion and environment probes.

table_name_for: underscore.pluralize with '/' replaced by '_' (e.g. 'Assistant::Chat' -> 'assistant_chats'). variable_name_for: underscore with '/' to '_' ('LLM::Chat' -> 'llm_chat'). controller_class_name_for: namespaced names become '<Namespace>::<ResourcePlural>Controller'; plain names '<Name.pluralize>Controller'. partial_path_for: '<underscore.pluralize>/<demodulize.underscore>' ('LLM::Message' -> 'llm/messages/message'). migration_version: '[<MAJOR>.<MINOR>]' from Rails::VERSION. postgresql?/mysql?: check ActiveRecord connection adapter_name downcased substring, returning false on any StandardError. table_exists?: delegates to ActiveRecord connection.table_exists?, also false on any StandardError, so database errors are reported as 'table missing'.

<a id="u-83dfe3b53c52"></a>
### `add_association_params`

`def add_association_params(params, default_assoc, table_name, model_name, owner_table…` · [lib/generators/ruby_llm/generator_helpers.rb:L144-L159][f1]

Builds the option list for acts_as_* declarations by appending only non-default association settings.

It derives the association symbol (plural table name if plural:, else singularized table name), the default foreign key '<assoc>_id', and computes the actual foreign key: for has_many/has_one (plural flag, or default_assoc already plural) it is '<owner_table.singularize>_id' on the associated table; for belongs_to it is '<table_name.singularize>_id' on the owner. It appends '<assoc>: :<assoc>' when the derived name differs from the default, '<assoc>_class: '<model_name>'' when model_name differs from assoc.classify, and '<assoc>_foreign_key: :<fk>' when the foreign key differs from the default. Private helper shared by the acts_as_* builders.

<a id="u-87f219d97f09"></a>
### `generator_helpers-acts-as-declarations`

`def acts_as_chat_declaration` · [lib/generators/ruby_llm/generator_helpers.rb:L52-L61][f1]

Four sibling builders that render acts_as_* declaration strings with per-association options.

acts_as_chat_declaration passes :messages (plural, owner chat table), :model (owner chat table); acts_as_message_declaration passes :chat, :tool_calls (plural), :model (all owner message table); acts_as_model_declaration passes :chats (plural, owner model table); acts_as_tool_call_declaration passes :message (owner tool_call table). Each delegates to add_association_params, collects the returned option fragments, and returns 'acts_as_<x>' with ' ' + options joined by ', ' only when any options exist — otherwise the bare macro name, so default apps render plain acts_as_chat/acts_as_message/acts_as_model/acts_as_tool_call.

calls: [add_association_params](r2-generator-helpers.md#u-83dfe3b53c52)

<a id="u-01ee1710a2b8"></a>
### `create_namespace_modules`

`def create_namespace_modules` · [lib/generators/ruby_llm/generator_helpers.rb:L94-L118][f1]

Creates wrapper namespace modules for namespaced model names.

It collects the first '::' segment of any chat/message/tool_call/model name that is namespaced, de-duplicated. For each namespace it skips creation if app/models/<namespace.underscore>.rb already exists under Rails.root; otherwise it creates the file defining 'module <Namespace>' with 'def self.table_name_prefix "<namespace underscore>_"'. File creation is the only side effect; existing namespace files are left untouched.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/generator_helpers.rb