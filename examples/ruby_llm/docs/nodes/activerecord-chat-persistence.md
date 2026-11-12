# ActiveRecord Chat Persistence

**Capability.** Wires chat, message, model, and tool-call records to persistence callbacks, associations, and conversion helpers.

Observed units show ActiveRecord acts_as macros and record-to-RubyLLM conversion. They include legacy and current persistence paths, callbacks, and model/message methods.

**Depends on.**

- [Core Chat Configuration](core-chat-configuration.md) · graph-confirmed · 2 edge(s) · ActiveRecord chat persistence uses core chat configuration for chat setup and orchestration.
- [Attachment And Content Handling](attachment-and-content-handling.md) · graph-only · 4 edge(s)
- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 2 edge(s)

Parent: [Chat Persistence And Orchestration](chat-persistence-and-orchestration.md)

## Units (27)

<a id="u-2a8609ac2791"></a>
### `acts_as.rb-activerecord-association-macros`

`def acts_as_chat(messages: :messages, message_class: nil, messages_foreign_key: nil, …` · [lib/ruby_llm/active_record/acts_as.rb:L34-L69][f1]

These class macros wire chat, model, message, and tool-call records to persistence modules and associations.

- Chat macro: includes ChatMethods; sets class attributes; defaults message/model classes by classify; has_many messages ordered created_at asc with dependent destroy; belongs_to model optional; delegates add_message; defines readers and a model_association= writer.
- Model macro: includes ModelMethods; defaults chat class by classify; validates model_id presence and uniqueness scoped to provider, provider presence, and name presence; has_many chats; defines a chats reader.
- Message macro: includes MessageMethods; defaults chat/tool-call/model classes by classify; belongs_to chat with touch option; has_many tool_calls dependent destroy; belongs_to parent_tool_call using tool_call_class and a foreign key from the singularized tool-calls name, optional; has_many tool_results through tool_calls source result class_name current model; belongs_to model optional; delegates predicates; defines readers.
- Tool-call macro: includes no module; defaults message class by classify and result class to message class, not by classifying the result association; belongs_to message required; has_one result dependent nullify; defines readers.

<a id="u-eec4c0698638"></a>
### `acts_as.rb-database-model-registry-monkey-patch`

`def self.included(base)` · [lib/ruby_llm/active_record/acts_as.rb:L10-L14][f1]

The included hook reopens RubyLLM::Models and installs database-backed model loading with a JSON fallback.

- On inclusion: calls super, then class_eval on RubyLLM::Models.
- Class load_models: calls read_from_database; rescues StandardError, logs debug, and calls read_from_json.
- Class read_from_database: resolves the configured registry class, constantizes it when it is a String, and maps all records through to_llm.
- Instance load_from_database!: sets @models to self.class.read_from_database.

**Uncertainties.**

- read_from_json is called but not defined in this file; its behavior is not established.

<a id="u-d9e4ab595c18"></a>
### `acts_as_legacy.rb-legacy-association-macros`

`def acts_as_chat(message_class: 'Message', tool_call_class: 'ToolCall')` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L10-L23][f2]

These legacy class macros wire chat, message, and tool-call records using fixed default class names and computed foreign keys.

- Chat macro: includes ChatLegacyMethods; stores message/tool-call class names; has_many messages ordered created_at asc inverse_of chat dependent destroy; delegates add_message.
- Message macro: includes MessageLegacyMethods; defaults chat/tool-call classes; computes foreign keys via foreign_key when nil; belongs_to chat inverse_of messages with touch option; has_many tool_calls dependent destroy; belongs_to parent_tool_call optional inverse_of result; has_many tool_results through tool_calls source result class_name @message_class; delegates predicates.
- Tool-call macro: defaults message class; computes message/result foreign keys; belongs_to message inverse_of tool_calls; has_one result inverse_of parent_tool_call dependent nullify.

**Uncertainties.**

- The message macro's tool_results association uses @message_class, but that macro does not assign it; the resulting class_name is not established from this file.

<a id="u-aad2ac61423a"></a>
### `acts_as_legacy.rb-legacy-attachment-persistence`

`def persist_content(message_record, attachments)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L293-L298][f2]

Normalizes attachment inputs and attaches them to a record only when the record supports attachments.

- persist_content: returns unless the record responds to attachments; prepares attachables; attaches them when any remain.
- prepare_for_active_storage: uses a safe array and filter_map; UploadedFile/Blob pass through; Attached::One/Many become blobs; Hash values recurse; other values convert; results are flattened and compacted.
- convert_to_active_storage_format: returns nil for a blank source before wrapping; uses an existing RubyLLM::Attachment or wraps the source; returns a hash with StringIO content, filename, and mime type; rescues StandardError, logs a warning, and returns nil.

<a id="u-031c5ec40f41"></a>
### `acts_as_legacy.rb-legacy-callback-wrappers`

`def on_new_message(&block)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L154-L164][f2]

Registers new-message and end-message callbacks while preserving any existing callback on the memoized chat.

Each calls to_llm, reads the existing callback from the chat's callback hash, registers a wrapper that calls the existing callback then the new block, and returns self; the end-message wrapper passes the message to both.

<a id="u-c492f29fc1df"></a>
### `acts_as_legacy.rb-legacy-chainable-delegators`

`def with_tool(...)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L114-L117][f2]

These chainable methods forward their arguments to the memoized chat and return the record.

Each calls the corresponding chat method and returns self; none persists changes directly.

<a id="u-2f910a780150"></a>
### `acts_as_legacy.rb-legacy-chat-construction-and-context`

`def to_llm(context: nil) # model_id is a string that RubyLLM can resolve` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L89-L103][f2]

The legacy conversion method memoizes a RubyLLM chat, rebuilds its messages from records, and installs persistence callbacks.

- to_llm: @chat ||= context ? context.chat(model: model_id) : RubyLLM.chat(model: model_id); resets messages; adds each message.to_llm; sets up callbacks; returns @chat.
- with_context: calls to_llm(context: context) and returns self; because @chat is memoized with ||=, an existing chat is reused and the new context is ignored.

<a id="u-644d4fb55709"></a>
### `acts_as_legacy.rb-legacy-completion-failure-cleanup`

`def complete(...)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L201-L207][f2]

Runs completion and, on RubyLLM errors, removes failed or orphaned persistence records before re-raising.

- complete: calls the chat completion; rescues RubyLLM::Error; if @message is persisted and its content is blank, calls cleanup_failed_messages; always calls cleanup_orphaned_tool_results; re-raises.
- cleanup_failed_messages: logs a warning and destroys @message.
- cleanup_orphaned_tool_results: reloads messages and takes the last by id; returns unless it is a tool call or tool result; destroys a last tool call; for a last tool result, finds the parent tool-call message, compares sorted expected tool-call ids with actual result tool_call_ids, and on mismatch destroys all tool results then the tool-call message.

<a id="u-362a59f86e3c"></a>
### `acts_as_legacy.rb-legacy-message-conversion`

`def to_llm` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L339-L349][f2]

Converts a legacy message record into a RubyLLM message, including tool calls and downloaded attachments.

- to_llm: builds RubyLLM::Message with role symbol, extracted content, tool calls, parent tool-call id, tokens, and model id.
- extract_tool_calls: maps tool_calls to a hash keyed by tool_call_id with RubyLLM::ToolCall id/name/arguments.
- extract_tool_call_id: returns the parent tool call's tool_call_id or nil.
- extract_content: returns content unless attachments are attached; otherwise builds RubyLLM::Content, initializes a tempfile list, downloads each attachment to a tempfile, and adds it with filename.
- download_attachment: creates a binmode Tempfile with basename/ext, writes downloaded chunks, flushes/rewinds, stores the tempfile, and returns it.

<a id="u-805fa4a48e2a"></a>
### `acts_as_legacy.rb-legacy-persistence-callbacks`

`def setup_persistence_callbacks` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L236-L244][f2]

Installs one-time persistence callbacks and writes assistant completions, tool calls, and tool-call links.

- setup: returns @chat if the setup flag is set; otherwise registers new-message and end-message persistence callbacks, sets the flag, and returns @chat.
- persist_new_message: creates an assistant message with empty content.
- persist_message_completion: returns unless a message is given; finds a tool-call id when the message has one; in a transaction, captures attachments and text from RubyLLM::Content or JSON-encodes Hash/Array content, updates role/content/model/tokens, writes the tool-call foreign key when found, saves, persists captured attachments, and persists tool calls when present.
- persist_tool_calls: creates each tool call after renaming id to tool_call_id.
- find_tool_call_id: constantizes the tool-call class, finds by tool_call_id, and returns its id or nil.

<a id="u-dee6f7fac611"></a>
### `acts_as_legacy.rb-legacy-user-message-and-ask`

`def create_user_message(content, with: nil)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L188-L192][f2]

Creates a user message record, optionally persists attachments, and can immediately complete the chat.

The create method saves role user with the given content and persists attachments when present; ask creates that message then calls complete and returns the completion result.

<a id="u-193671a7b499"></a>
### `chat_methods.rb-chat-attachment-and-content-normalization`

`def persist_content(message_record, attachments)` · [lib/ruby_llm/active_record/chat_methods.rb:L306-L311][f3]

Normalizes content and attachment inputs for storage, attaching only when the record supports attachments.

- persist_content: returns unless the record responds to attachments; prepares attachables; attaches them when any remain.
- prepare_for_active_storage: uses a safe array and filter_map; UploadedFile/Blob pass through; Attached::One/Many become blobs; Hash values recurse; other values convert; results are flattened and compacted.
- convert_to_active_storage_format: returns nil for a blank source before wrapping; uses an existing RubyLLM::Attachment or wraps the source; returns a hash with StringIO content, filename, and mime type; rescues StandardError, logs a warning, and returns nil.
- prepare_content_for_storage: Raw becomes content_raw with nil text; Content captures attachments when any and uses text; Hash/Array becomes content_raw with nil text; other values remain text; returns text, attachments, and raw content.

<a id="u-3874ab3236bf"></a>
### `chat_methods.rb-chat-callback-wrappers`

`def on_new_message(&block)` · [lib/ruby_llm/active_record/chat_methods.rb:L142-L152][f3]

Registers new-message and end-message callbacks while preserving any existing callback on the memoized chat.

Each calls to_llm, reads the existing callback from the chat's callback hash, registers a wrapper that calls the existing callback then the new block, and returns self; the end-message wrapper passes the message to both.

<a id="u-ae8c65a5ed42"></a>
### `chat_methods.rb-chat-chainable-delegators`

`def with_tool(...)` · [lib/ruby_llm/active_record/chat_methods.rb:L102-L105][f3]

These chainable methods forward their arguments to the memoized chat and return the record.

Each calls the corresponding chat method and returns self; none persists changes directly.

<a id="u-388b172be37e"></a>
### `chat_methods.rb-chat-completion-failure-cleanup`

`def complete(...)` · [lib/ruby_llm/active_record/chat_methods.rb:L197-L203][f3]

Runs completion and, on RubyLLM errors, removes failed or orphaned persistence records before re-raising.

- complete: calls the chat completion; rescues RubyLLM::Error; if @message is persisted and its content is blank, calls cleanup_failed_messages; always calls cleanup_orphaned_tool_results; re-raises.
- cleanup_failed_messages: logs a warning and destroys @message.
- cleanup_orphaned_tool_results: reloads the messages association and takes the last by id; returns unless it is a tool call or tool result; destroys a last tool call; for a last tool result, finds the parent tool-call message, compares sorted expected tool-call ids with actual result tool_call_ids, and on mismatch destroys all tool results then the tool-call message.

<a id="u-f15b0942c6e5"></a>
### `chat_methods.rb-chat-model-provider-accessors`

`def model=(value)` · [lib/ruby_llm/active_record/chat_methods.rb:L15-L24][f3]

These accessors defer string model/provider assignment and read resolved values from the model association.

- model=: a String stores @model_string and returns; a non-String assigns through super when the association name is :model, otherwise through model_association=.
- model_id=: stores @model_string.
- model_id: returns model_association&.model_id.
- provider=: stores @provider_string.
- provider: returns model_association&.provider.

<a id="u-58c734552733"></a>
### `chat_methods.rb-chat-persistence-callbacks`

`def setup_persistence_callbacks` · [lib/ruby_llm/active_record/chat_methods.rb:L232-L240][f3]

Installs one-time persistence callbacks and writes assistant completions, tool calls, and tool-call links.

- setup: returns @chat if the setup flag is set; otherwise registers new-message and end-message persistence callbacks, sets the flag, and returns @chat.
- persist_new_message: creates an assistant message with empty content.
- persist_message_completion: returns unless a message is given; finds a tool-call id when the message has one; in a transaction, normalizes content, builds role/content/token attributes, adds cached and cache-creation tokens only when the columns exist, sets the model association attribute, sets the parent tool-call foreign key when found, assigns and saves, persists attachments when present, and persists tool calls when present.
- persist_tool_calls: creates each tool call through the tool-calls association after renaming id to tool_call_id.
- find_tool_call_id: joins messages to the tool-calls association, finds the message by tool_call_id, then finds the tool call and returns its id or nil.

<a id="u-9184253bc810"></a>
### `chat_methods.rb-chat-user-message-and-ask`

`def create_user_message(content, with: nil)` · [lib/ruby_llm/active_record/chat_methods.rb:L176-L188][f3]

Creates a user message with normalized content and attachments, and can immediately complete the chat.

The create method prepares content, builds role user, sets content and content_raw when supported, saves, persists explicit attachments when present, persists content attachments when present, and returns the record; ask creates that message then calls complete and returns the completion result.

<a id="u-39b038a4fcb5"></a>
### `message_methods.rb-message-conversion-helpers`

`def extract_tool_calls` · [lib/ruby_llm/active_record/message_methods.rb:L32-L43][f4]

Extracts tool calls, parent tool-call id, content, and downloaded attachments from a message record.

- extract_tool_calls: maps the tool-calls association to a hash keyed by tool_call_id with RubyLLM::ToolCall id/name/arguments.
- extract_tool_call_id: returns the parent tool call's tool_call_id or nil.
- extract_content: returns Raw content when the content_raw column exists and is present; otherwise returns content unless attachments are attached; otherwise builds RubyLLM::Content, initializes a tempfile list, downloads each attachment to a tempfile, and adds it with filename.
- download_attachment: creates a binmode Tempfile with basename/ext, writes downloaded chunks, flushes/rewinds, stores the tempfile, and returns it.

<a id="u-ba3752f34f02"></a>
### `model_methods.rb-model-registry-persistence-and-conversion`

`def refresh!` · [lib/ruby_llm/active_record/model_methods.rb:L10-L22][f5]

Refreshes or saves model registry records and converts between database rows and RubyLLM model info.

- refresh!: refreshes RubyLLM models, then in a transaction upserts every model by model_id/provider with converted attributes.
- save_to_database: performs the same upsert without refreshing first.
- from_llm: builds an unsaved new record from converted attributes.
- from_llm_attributes: maps id/name/provider/family/created_at/context_window/max_output_tokens/knowledge_cutoff/modalities/capabilities/pricing/metadata.
- to_llm: builds RubyLLM::Model::Info with deep-symbolized modalities/pricing/metadata or empty hashes; the module delegates support, pricing, and provider queries to this conversion.

<a id="u-f7e3cc8b27db"></a>
### `with_instructions`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L105-L112][f2]

Adds a system instruction message and forwards the instruction to the memoized chat.

It runs in a transaction, destroys existing system messages when replace is true, creates a new system message, then calls the chat instruction method and returns self.

<a id="u-e83096d321c4"></a>
### `with_model`

`def with_model(...)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L124-L127][f2]

Switches the chat model through the memoized chat and persists the resolved model id.

It updates the record with the id returned by the chat model switch and returns self.

<a id="u-7544ece9d979"></a>
### `resolve_model_from_strings`

`def resolve_model_from_strings # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/active_record/chat_methods.rb:L44-L74][f3]

Resolves deferred model/provider strings into a model record before saving, creating missing records but not updating existing ones.

It uses context config or global config, falls back to the default model when no association exists, resolves model info, constantizes the model class, and find_or_create_by! on model_id/provider; the block fills attributes only on create, so existing records are not updated. It then assigns the association and clears the deferred strings; resolution or persistence errors are not rescued here.

<a id="u-59d9b4cae453"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:to_llm`

`def to_llm` · [lib/ruby_llm/active_record/chat_methods.rb:L78-L91][f3]

Builds or reuses a RubyLLM chat from the associated model and replays persisted messages into it.

It memoizes @chat with ||=, resets messages, adds each associated message's conversion, and sets up persistence callbacks; a missing model association is not guarded.

<a id="u-e2b62f76530f"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:with_instructions`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/active_record/chat_methods.rb:L93-L100][f3]

Adds a system instruction message and forwards the instruction to the memoized chat.

It runs in a transaction, destroys existing system messages when replace is true, creates a new system message, then calls the chat instruction method and returns self.

<a id="u-7f4552ac6ff1"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:with_model`

`def with_model(model_name, provider: nil, assume_exists: false)` · [lib/ruby_llm/active_record/chat_methods.rb:L112-L120][f3]

Switches the chat model, resolves and saves the model record, then forwards the switch to the memoized chat.

It sets the model string, optional provider, and assume-exists flag, resolves the model, saves the record, calls the chat model switch with the resolved id/provider, and returns self; save! can raise.

<a id="u-f8aea5d5092c"></a>
### `lib/ruby_llm/active_record/message_methods.rb:to_llm`

`def to_llm` · [lib/ruby_llm/active_record/message_methods.rb:L13-L28][f4]

Converts a message record into a RubyLLM message, including optional cache token columns and model id.

It reads cached_tokens and cache_creation_tokens only when those columns exist, then builds the message with role symbol, extracted content, tool calls, parent tool-call id, input/output tokens, cache values, and the associated model id.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/acts_as.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/acts_as_legacy.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/chat_methods.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/message_methods.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/model_methods.rb
