# ChatMethods Persistence

**Capability.** Implements the runtime API on chat models: model resolution and switching, memoized to_llm bridge, complete, and private persistence helpers that materialize assistant messages.

Read to trace a persisted chat from model= / with_model through complete to persisted message rows, including content splitting for storage.

**Depends on.**

- [acts\_as Declarations](r2-acts-as-declarations.md) · model-inferred · 0 edge(s)
- [Chat Session & Completion Loop](r1-chat-session.md) · graph-only · 1 edge(s)
- [Shared Utilities](r1-shared-utilities.md) · graph-only · 1 edge(s)

Parent: [ActiveRecord Integration](r2-active-record-integration.md)

## Units (9)

<a id="u-65ef3fdf9d92"></a>
### `chat_methods-callback-config-wrappers`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/active_record/chat_methods.rb:L93-L100][f1]

Configuration and callback wrappers on modern chat models.

with_instructions wraps in a transaction: when replace is true it destroys existing system-role messages, then creates a system message with the instructions, and applies with_instructions on to_llm, returning self; transaction failure leaves existing system messages intact. with_tool/with_tools/with_temperature/with_params/with_headers/with_schema/on_tool_call/on_tool_result forward arguments (via ...) to to_llm and return self without persisting anything. on_new_message and on_end_message force to_llm, read the chat's existing callback from the @on instance variable, and register a wrapper callback invoking the existing callback first and then the given block, so both execute. create_user_message splits its content via prepare_content_for_storage, builds and saves a user-role message (writing content_raw when the record supports it), and persists attachments from both the with: argument and content-derived attachments. ask (aliased say) creates the user message then calls complete with the given block.

calls: [prepare_content_for_storage](r2-chat-persistence.md#u-634edf43853f)

**Uncertainties.**

- The @on hash layout of the underlying chat object is defined in lib/ruby_llm/chat.rb, not here.

<a id="u-0769779e96c9"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:complete`

`def complete(...)` · [lib/ruby_llm/active_record/chat_methods.rb:L197-L203][f1]

Runs the LLM completion by delegating all arguments to to_llm.complete.

On RubyLLM::Error it repairs persisted state before re-raising: when @message is persisted with blank content, cleanup_failed_messages logs a warning and destroys it; cleanup_orphaned_tool_results then removes a trailing dangling tool call or an incomplete tool-call/result pair. The original error is always re-raised.

**Notes.**

- failure: A partially filled @message survives the failure; only blank assistant messages are destroyed.

calls: [chat_methods-persistence-helpers](r2-chat-persistence.md#u-e64cd93b45bb)

<a id="u-59d9b4cae453"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:to_llm`

`def to_llm` · [lib/ruby_llm/active_record/chat_methods.rb:L78-L91][f1]

Builds the in-memory chat from the persisted model association and messages, memoized in @chat.

The chat is created on (context || RubyLLM).chat with model: model_record.model_id and provider: model_record.provider.to_sym, so a context overrides global configuration; it always calls reset_messages! and replays every persisted message via @chat.add_message(msg.to_llm), then installs persistence callbacks once and returns the chat. Assumes model_association is present; a nil association would fail on model_record.model_id.

calls: [chat_methods-persistence-helpers](r2-chat-persistence.md#u-e64cd93b45bb); uses: [message_methods-content-extraction](r1-message-methods.md#u-92796b41699b)

<a id="u-7f4552ac6ff1"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:with_model`

`def with_model(model_name, provider: nil, assume_exists: false)` · [lib/ruby_llm/active_record/chat_methods.rb:L112-L120][f1]

Switches the chat's model persistently: sets the model string (and optional provider string) via the attribute writers, records assume_model_exists, invokes resolve_model_from_strings directly to create/find the model row, calls save!

so the before_save resolver and validation run, then applies with_model on to_llm using the persisted association's model_id and provider symbol, returning self. Any resolution or save failure aborts before the underlying chat is reconfigured.

calls: [resolve_model_from_strings](r2-chat-persistence.md#u-7544ece9d979)

<a id="u-66c4c9df2ea9"></a>
### `model=`

`def model=(value)` · [lib/ruby_llm/active_record/chat_methods.rb:L15-L24][f1]

Accepts either a model record or a model name string.

A String is stashed in @model_string for later resolution by resolve_model_from_strings and no association write happens. A non-String is written through the association: if the class's model_association_name is :model it calls the default ActiveRecord writer, otherwise it writes through the custom model_association= accessor defined by acts_as_chat.

contract: [resolve_model_from_strings](r2-chat-persistence.md#u-7544ece9d979)

<a id="u-7544ece9d979"></a>
### `resolve_model_from_strings`

`def resolve_model_from_strings # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/active_record/chat_methods.rb:L44-L74][f1]

Before-save resolver that turns @model_string/@provider_string into a persisted model association.

It picks config from @context when set, else RubyLLM.config; if there is no model association yet it defaults @model_string to config.default_model. When a model string is present it resolves model info via Models.resolve with the provider string, assume_exists flag and config, then find_or_create_by!(model_id, provider) on the class's model_class, filling name (falling back to the id), family, context_window, max_output_tokens, capabilities (default []), modalities/pricing/metadata (default {}). It assigns the model association and clears both strings. Find/create or resolution failures raise before save completes, since this runs as a before_save callback.

**Notes.**

- side_effect: Creates a model-registry row as a side effect of saving a chat when the model record does not yet exist.

contract: [ChatMethods][f1]

**Uncertainties.**

- Models.resolve failure modes and the meaning of assume_exists are defined outside this file.

<a id="u-235366884f29"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:persist_message_completion`

`def persist_message_completion(message)` · [lib/ruby_llm/active_record/chat_methods.rb:L247-L281][f1]

Finalizes the assistant message row created by persist_new_message once the completion ends; returns immediately for a nil message.

Inside a transaction it resolves the database tool_call id via find_tool_call_id when the LLM message has one, splits content through prepare_content_for_storage into text/attachments/content_raw, and assembles attributes: role, content text, input/output tokens, cached_tokens and cache_creation_tokens only when @message has those columns, the model association under the class's configured association name, and the parent_tool_call foreign key via reflection when a tool_call_id resolved. It assigns attributes, writes content_raw when supported, saves, then persists attachments via persist_content and creates tool-call rows via persist_tool_calls when present. Save or create failures abort the transaction, leaving @message as the empty assistant row created on new-message.

**Notes.**

- condition: Token-cache attributes are written only when the message table actually has cached_tokens / cache_creation_tokens columns (has_attribute? checks).

calls: [chat_methods-persistence-helpers](r2-chat-persistence.md#u-e64cd93b45bb)

**Uncertainties.**

- reflect_on_association(:parent_tool_call) is assumed to exist on the message class; a missing association would return a reflection whose foreign_key use may raise.

<a id="u-634edf43853f"></a>
### `prepare_content_for_storage`

`def prepare_content_for_storage(content)` · [lib/ruby_llm/active_record/chat_methods.rb:L343-L361][f1]

Splits content into a [text, attachments, raw] triple for persistence.

RubyLLM::Content::Raw yields raw = its value and nil text. A RubyLLM::Content yields its attachments (only when any exist) and its text. Hash or Array content is kept as raw with nil text. Anything else passes through unchanged as text with no attachments or raw value.

<a id="u-e64cd93b45bb"></a>
### `chat_methods-persistence-helpers`

`def cleanup_failed_messages` · [lib/ruby_llm/active_record/chat_methods.rb:L207-L210][f1]

Persistence plumbing syncing chat activity into rows (private).

setup_persistence_callbacks registers persist_new_message and persist_message_completion on the chat's new/end message callbacks once, guarded by the @_persistence_callbacks_setup flag, returning the chat. persist_new_message creates an empty assistant message row into @message. cleanup_failed_messages logs a warning and destroys @message (caller guarantees it is persisted). cleanup_orphaned_tool_results reloads messages and inspects the last by id: no changes unless it is a tool call or tool result; a trailing tool call is destroyed; a trailing tool result triggers comparison of the parent tool-call message's tool_call ids against its tool_results' tool_call_ids, destroying all tool_results and the tool-call message only when the sorted sets differ. persist_tool_calls maps each tool call hash, renaming :id to :tool_call_id, into @message's tool_calls association. find_tool_call_id joins the message table to its tool_calls association (resolved via reflection for table name) to find the message owning that tool_call_id, then returns that tool call row's id, or nil when nothing matches. persist_content attaches prepared attachables only when the record supports attachments. prepare_for_active_storage normalizes via Utils.to_safe_array: UploadedFile/Blob pass through, Attached::One/Many contribute blobs, Hash values recurse, everything else goes through convert_to_active_storage_format; results are flattened and compacted. convert_to_active_storage_format returns nil for blank input, wraps RubyLLM::Attachment or constructs one from the source, and yields io (StringIO of content)/filename/content_type, logging a warning and returning nil on any StandardError so a bad attachment is skipped, not fatal.

**Notes.**

- failure: cleanup_orphaned_tool_results dereferences last.parent_tool_call.message with no nil guard, so a missing parent raises.

calls: [utils-utils-helpers](r1-shared-utilities.md#u-add7cf7f30e5)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/chat_methods.rb