# ActiveRecord persistence bridge

**Capability.** Bridges ActiveRecord chat, message, tool-call, and model records to RubyLLM objects, persisting streamed completions and syncing the model registry.

Come here for database persistence of conversations: acts_as DSLs (current and legacy), callback wiring that saves new messages and completions, tool-call record creation, and record-to-Message/Chat conversion. ModelMethods keeps model records in sync with the registry, and Content wraps text plus attachments.

**Depends on.**

- [Chat Orchestration and Gem Facade](chat-orchestration-and-gem-facade.md) · graph-confirmed · 2 edge(s) · The ActiveRecord bridge builds and drives Chat objects from persisted records.
- [Gemini and media integrations](gemini-and-media-integrations.md) · graph-only · 3 edge(s)
- [Chat conversation orchestration](chat-conversation-orchestration.md) · graph-only · 2 edge(s)
- [Attachment Normalization and MIME](attachment-normalization-and-mime.md) · graph-only · 1 edge(s)

Parent: [Persistence and Conversation Layer](persistence-and-conversation-layer.md)

## Units (27)

<a id="u-1bb3c1f5b19a"></a>
### `acts_as.rb-acts-as-dsl-macros`

`def acts_as_chat(messages: :messages, message_class: nil, messages_foreign_key: nil, …` · [lib/ruby_llm/active_record/acts_as.rb:L34-L69][f1]

Class methods that wire ActiveRecord associations and include the matching behavior module.

acts_as_chat includes ChatMethods, stores association/class names as class_attributes, sets has_many messages (ordered by created_at, dependent: :destroy) and an optional belongs_to model, delegates add_message to to_llm, and defines messages_association/model_association accessors (plus model_association=). acts_as_model includes ModelMethods, sets chats has_many, and validates presence of model_id (unique per provider), provider, and name. acts_as_message includes MessageMethods, sets belongs_to chat (optionally touching), has_many tool_calls (dependent: :destroy), optional belongs_to parent_tool_call (foreign key derived from the tool_calls name), has_many tool_results through tool_calls (source :result, class_name = own class), optional belongs_to model, delegates tool_call?/tool_result? to to_llm, and defines association accessors. acts_as_tool_call sets class attributes and a required belongs_to message plus has_one result with dependent: :nullify, defining message_association/result_association accessors. Class names default via classify on the association name; foreign keys are optional overrides.

<a id="u-3c3d79ac12ec"></a>
### `acts_as.rb-actsas-concern-and-models-monkey-patch`

`module ActsAs` · [lib/ruby_llm/active_record/acts_as.rb:L6-L10][f1]

Concern that, when included, monkey-patches RubyLLM::Models so model loading prefers the database.

The included hook reopens RubyLLM::Models::Singleton (class_eval): load_models calls read_from_database and, on any StandardError, logs a debug message and falls back to read_from_json; read_from_database resolves RubyLLM.config.model_registry_class (constantizing Strings) and maps all records through to_llm; load_from_database! refreshes @models from the database. Side effect is global: the patch applies to RubyLLM::Models itself, not just the including class, once this concern is included anywhere.

<a id="u-e9ca42c6a849"></a>
### `acts_as_legacy.rb-legacy-acts-as-macros`

`module ActsAsLegacy` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L6-L10][f2]

Legacy DSL that hardcodes association names.

acts_as_chat includes ChatLegacyMethods, stores message/tool-call class names in class-level ivars, sets has_many :messages (ordered, inverse_of, dependent: :destroy) and delegates add_message to to_llm. acts_as_message includes MessageLegacyMethods and sets belongs_to :chat (foreign key defaults to the chat class's foreign key, optional touch), has_many :tool_calls (dependent: :destroy), optional belongs_to :parent_tool_call (foreign key defaults to the tool-call class's foreign key, inverse_of :result), has_many :tool_results through :tool_calls, and delegates tool_call?/tool_result? to to_llm. acts_as_tool_call sets belongs_to :message (inverse_of :tool_calls) and has_one :result (foreign key defaults to this class's own foreign key, dependent: :nullify). Unlike the modern macros, class names live in instance-variable-backed attr_readers rather than class_attributes.

<a id="u-f1c7f18d8816"></a>
### `acts_as_legacy.rb-legacy-ask-complete-entry-points`

`def create_user_message(content, with: nil)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L188-L192][f2]

create_user_message creates a user message (role :user, given content) and, if a with: attachment payload is present, persists it via persist_content, returning the record.

ask creates the user message then calls complete with the passed block (aliased as say). complete delegates to to_llm.complete; on RubyLLM::Error it destroys the blank persisted assistant message (cleanup_failed_messages, with a warning log), removes orphaned tool results (cleanup_orphaned_tool_results), and re-raises the original error.

<a id="u-b4de48a4997b"></a>
### `acts_as_legacy.rb-legacy-callback-registration`

`def on_new_message(&block)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L154-L164][f2]

on_new_message/on_end_message wrap existing chat callbacks: they force to_llm, read the current callback from the chat's @on hash, and re-register a block that calls the existing callback first (with the message for end_message) then the user block, returning self.

on_tool_call/on_tool_result simply forward to the chat and return self.

<a id="u-67097993033e"></a>
### `acts_as_legacy.rb-legacy-chat-to-llm`

`module ChatLegacyMethods` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L82-L89][f2]

ChatLegacyMethods module (mixed into legacy chat models) whose to_llm builds and memoizes a RubyLLM chat.

It creates the chat via context.chat(model: model_id) when a context is given, else RubyLLM.chat(model: model_id); memoizes in @chat; resets the chat's messages; replays every persisted message by calling msg.to_llm and add_message; then registers persistence callbacks via setup_persistence_callbacks and returns the chat. Repeated calls reuse @chat but always reset and replay, so in-memory chat state mirrors the database.

<a id="u-4e4579c385ea"></a>
### `acts_as_legacy.rb-legacy-failure-cleanup`

`def cleanup_failed_messages` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L211-L214][f2]

cleanup_failed_messages logs a warning and destroys @message.

cleanup_orphaned_tool_results reloads messages and examines the last by id: it returns unless the last is a tool_call? or tool_result?; a trailing tool_call message is destroyed; for a tool_result it compares the parent tool-call message's expected tool_call ids (from its tool_calls) against actual result tool_call_ids, and if the sorted lists differ it destroys all of that message's tool_results and the message itself.

<a id="u-5c9f74bc2bf3"></a>
### `acts_as_legacy.rb-legacy-message-extraction`

`module MessageLegacyMethods` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L349-L353][f2]

extract_tool_calls maps the tool_calls association into a hash keyed by tool_call_id with RubyLLM::ToolCall values (id, name, arguments).

extract_tool_call_id returns parent_tool_call's tool_call_id. extract_content returns the raw content unless the record has attached attachments, in which case it builds a RubyLLM::Content and adds each attachment as a downloaded tempfile (tracked in @_tempfiles to delay cleanup). download_attachment streams the blob into a binmode Tempfile named after the attachment's filename, flushes, rewinds, records it in @_tempfiles, and returns it.

<a id="u-6763cb1798ca"></a>
### `acts_as_legacy.rb-legacy-message-to-llm`

`module MessageLegacyMethods` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L332-L339][f2]

MessageLegacyMethods module (mixed into legacy message models) whose to_llm converts the record into a RubyLLM::Message with symbolized role, extracted content, tool_calls, tool_call_id, token counts, and model_id.

Extraction details live in the sibling unit.

<a id="u-37e048e7b7a0"></a>
### `acts_as_legacy.rb-legacy-persistence-internals`

`def setup_persistence_callbacks` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L236-L244][f2]

setup_persistence_callbacks is idempotent via a @_persistence_callbacks_setup flag on the chat: on first call it registers on_new_message → persist_new_message and on_end_message → persist_message_completion.

persist_new_message creates an assistant message with empty content in @message. persist_message_completion returns unless a message was yielded; resolves the parent tool-call record id when the message has a tool_call_id, then in a transaction normalizes content (RubyLLM::Content → text plus attachments; Hash/Array → JSON), updates @message with role/content/model_id/token counts, writes the tool-call foreign key when present, saves, persists attachments and any tool_calls. persist_tool_calls creates a tool-call record per entry, renaming :id to :tool_call_id. find_tool_call_id looks up the tool-call class by tool_call_id and returns its record id. persist_content attaches prepared blobs only if the record responds to attachments. prepare_for_active_storage flattens the input (via Utils.to_safe_array), passing through UploadedFile/Blob, expanding Attached to blobs, recursing into Hash values, and converting anything else via convert_to_active_storage_format, which wraps non-Attachment sources in RubyLLM::Attachment and returns an {io, filename, content_type} hash, logging a warning and returning nil on any StandardError.

<a id="u-f49e68405eac"></a>
### `acts_as_legacy.rb-legacy-with-delegators`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L105-L112][f2]

Fluent configurators that mostly delegate to the memoized to_llm chat and return self.

with_instructions is the exception: inside a transaction it destroys existing system messages when replace: true, creates a new system message, then forwards instructions to the chat. with_model updates the record's model_id from the resolved chat model. with_context re-builds to_llm with the given context. with_tool/with_tools/with_temperature/with_params/with_headers/with_schema are pure pass-through forwarding with (...) and return self.

<a id="u-018f503a6335"></a>
### `chat_methods.rb-ask-complete-entry-points`

`def create_user_message(content, with: nil)` · [lib/ruby_llm/active_record/chat_methods.rb:L176-L188][f3]

create_user_message normalizes content via prepare_content_for_storage, builds a user message, sets content and content_raw (only if the record has that attribute), saves, then persists the with: attachments and any attachments extracted from the content, returning the record.

ask creates the user message then completes with the passed block (aliased as say). complete delegates to to_llm.complete; on RubyLLM::Error it destroys the blank persisted assistant message, cleans orphaned tool results, and re-raises.

<a id="u-f38afbb4e7f9"></a>
### `chat_methods.rb-attachment-and-content-normalization`

`def prepare_for_active_storage(attachments)` · [lib/ruby_llm/active_record/chat_methods.rb:L313-L326][f3]

persist_content attaches prepared blobs only when the record responds to attachments.

prepare_for_active_storage flattens input via Utils.to_safe_array, passing through UploadedFile/Blob, expanding Attached::One/Many to blobs, recursing into Hash values, and converting the rest via convert_to_active_storage_format (wraps non-Attachment sources in RubyLLM::Attachment, returns {io, filename, content_type}, logging a warning and returning nil on StandardError). prepare_content_for_storage splits content into [text, attachments, raw]: RubyLLM::Content::Raw yields raw value with nil text; RubyLLM::Content yields text plus attachments when present; Hash/Array become raw with nil text; anything else passes through as text.

<a id="u-b5052934f617"></a>
### `chat_methods.rb-callback-registration`

`def on_new_message(&block)` · [lib/ruby_llm/active_record/chat_methods.rb:L142-L152][f3]

on_new_message/on_end_message force to_llm, read the chat's existing callback from its @on hash, and re-register a wrapper that invokes the existing callback first (passing the message for end_message) then the user's block, returning self.

on_tool_call/on_tool_result forward directly to the chat and return self.

<a id="u-008f8a45e1b6"></a>
### `chat_methods.rb-failure-cleanup`

`def cleanup_failed_messages` · [lib/ruby_llm/active_record/chat_methods.rb:L207-L210][f3]

cleanup_failed_messages warns and destroys @message.

cleanup_orphaned_tool_results reloads the messages association and inspects the last message by id: returns unless it is a tool_call? or tool_result?; a trailing tool_call message is destroyed; for a tool_result it compares the parent tool-call message's expected tool_call ids against actual result tool_call_ids and, on mismatch, destroys all its tool_results and the message itself.

<a id="u-d65199b2e7c4"></a>
### `chat_methods.rb-model-provider-attribute-bridging`

`module ChatMethods` · [lib/ruby_llm/active_record/chat_methods.rb:L6-L15][f3]

ChatMethods module (mixed into chat models) that bridges string model references to the model association.

On include it registers before_save :resolve_model_from_strings and declares attr_accessors assume_model_exists and context. model= stores Strings in @model_string for later resolution and otherwise assigns the association (super when the association is literally :model, else model_association=). model_id= only stores @model_string; model_id and provider read through the model association. provider= stores @provider_string. So assigning strings defers resolution until save.

<a id="u-5f03fd55b1f6"></a>
### `chat_methods.rb-persistence-callbacks-and-completion`

`def setup_persistence_callbacks` · [lib/ruby_llm/active_record/chat_methods.rb:L232-L240][f3]

setup_persistence_callbacks is idempotent via @_persistence_callbacks_setup on the chat, registering on_new_message → persist_new_message and on_end_message → persist_message_completion.

persist_new_message creates an assistant message with empty content in @message. persist_message_completion returns unless a message was yielded; resolves the parent tool-call record id when present, then in a transaction normalizes content via prepare_content_for_storage, builds attributes (role, content, token counts, plus cached_tokens/cache_creation_tokens only if @message has those columns), adds the model association and the parent_tool_call foreign key when applicable, assigns and saves, sets content_raw if supported, and persists attachments and tool_calls when present.

<a id="u-8463b01d202f"></a>
### `chat_methods.rb-tool-call-persistence`

`def persist_tool_calls(tool_calls)` · [lib/ruby_llm/active_record/chat_methods.rb:L284-L290][f3]

persist_tool_calls creates one record per tool call on @message's tool_calls_association, renaming :id to :tool_call_id.

find_tool_call_id joins the messages association through the tool-calls association table and finds the message owning the given tool_call_id, then returns that tool-call record's id, or nil if not found.

<a id="u-f4815a68df84"></a>
### `chat_methods.rb-with-configurators`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/active_record/chat_methods.rb:L93-L100][f3]

Fluent configurators returning self.

with_instructions transactionally destroys existing system messages when replace: true, creates a new system message, then forwards to the chat. with_model is the heavyweight one: it sets the model string (and provider if given), sets assume_model_exists, resolves immediately, saves the record, then forwards the resolved model to the chat. with_tool/with_tools/with_temperature/with_params/with_headers/with_schema are pass-through delegations to the memoized chat.

<a id="u-85b98368732e"></a>
### `content.rb-content-raw-passthrough`

`class Raw` · [lib/ruby_llm/content.rb:L55-L58][f4]

Marks a provider-specific payload to bypass RubyLLM's content formatting.

initialize raises ArgumentError on nil; format and to_h both return the stored value unchanged.

<a id="u-c1e52bfd7115"></a>
### `content.rb-content-value-object`

`class Content` · [lib/ruby_llm/content.rb:L5-L8][f4]

Wraps text plus attachments for LLM payloads.

initialize accepts text and attachments; attachments are normalized via process_attachments (Hash values each processed, anything else passed through process_attachments_array_or_string, which uses Utils.to_safe_array and adds each element as an Attachment), then raises ArgumentError if both text is nil and attachments ended up empty. add_attachment appends an Attachment and returns self. format returns the plain string when there is text and no attachments, otherwise self, letting callers pass strings through unchanged. to_h serializes as {text:, attachments: [each.to_h]} for Rails.

calls: [Attachment](../../catalog.json.gz), [utils.rb-data-utilities](gemini-and-media-integrations.md#u-907fb557c5e2)

**Uncertainties.**

- Attachment's constructor behavior (source not in batch) is unproven; a failure there would propagate out of initialize/add_attachment.

<a id="u-7d382c26140b"></a>
### `message_methods.rb-message-extraction`

`module MessageMethods` · [lib/ruby_llm/active_record/message_methods.rb:L28-L32][f5]

extract_tool_calls maps the tool_calls_association into a hash keyed by tool_call_id with RubyLLM::ToolCall values.

extract_tool_call_id returns parent_tool_call's tool_call_id. extract_content prefers content_raw (as RubyLLM::Content::Raw) when that column exists and is present; otherwise returns the content column unless attachments are attached, in which case it builds a RubyLLM::Content and adds each attachment as a downloaded tempfile tracked in @_tempfiles. download_attachment streams the blob into a binmode Tempfile named from the attachment filename, flushes, rewinds, records it in @_tempfiles, and returns it.

<a id="u-5831c9837611"></a>
### `message_methods.rb-message-to-llm`

`module MessageMethods` · [lib/ruby_llm/active_record/message_methods.rb:L6-L13][f5]

MessageMethods module (mixed into message models) whose to_llm builds a RubyLLM::Message with symbolized role, extracted content, tool_calls, tool_call_id, token counts, cached_tokens/cache_creation_tokens (only when those columns exist, else nil), and the model association's model_id.

Extraction details live in the sibling unit.

<a id="u-41528d62d94f"></a>
### `model_methods.rb-model-registry-sync`

`module ModelMethods` · [lib/ruby_llm/active_record/model_methods.rb:L6-L10][f6]

ModelMethods class-level API for keeping model records in sync with RubyLLM's registry.

refresh! calls RubyLLM.models.refresh! then, in a transaction, find_or_initialize_by model_id/provider for every registry model and updates each with from_llm_attributes. save_to_database does the same transaction loop without refreshing the registry first. from_llm returns a new unsaved record built from a model_info. from_llm_attributes (private) maps the registry info's fields (id, name, provider, family, created_at, context_window, max_output_tokens, knowledge_cutoff, modalities/pricing as hashes, capabilities, metadata) to record attributes.

<a id="u-8cb4047948c5"></a>
### `model_methods.rb-modelmethods`

`module ModelMethods` · [lib/ruby_llm/active_record/model_methods.rb:L57-L60][f6]

Instance-level conversion of a model record back into a RubyLLM::Model::Info, deep-symbolizing modalities, pricing, and metadata (defaulting to empty hashes when nil).

The module also delegates capability queries (supports?, supports_vision?, supports_functions?, type, pricing helpers, function_calling?, structured_output?, batch?, reasoning?, citations?, streaming?, provider_class) to that Info, so the record answers registry questions directly.

<a id="u-7544ece9d979"></a>
### `resolve_model_from_strings`

`def resolve_model_from_strings # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/active_record/chat_methods.rb:L44-L74][f3]

Resolves deferred @model_string/@provider_string into the model association before save.

Uses the context's config (falling back to RubyLLM.config); if no association is set and no string was given, defaults @model_string to config.default_model. Returns early if no string remains. Otherwise resolves via Models.resolve (honoring assume_model_exists), then find_or_create_by! on the model class by model_id/provider, filling name/family/context_window/max_output_tokens/capabilities/modalities/pricing/metadata on create; assigns the association and clears both strings. Resolution or creation failures propagate and abort the save.

<a id="u-59d9b4cae453"></a>
### `lib/ruby_llm/active_record/chat_methods.rb:to_llm`

`def to_llm` · [lib/ruby_llm/active_record/chat_methods.rb:L78-L91][f3]

Builds and memoizes the RubyLLM chat from the persisted model record: creates it via (context || RubyLLM).chat with the record's model_id and symbolized provider, memoizes in @chat, resets messages, replays each message of the messages_association through add_message, then registers persistence callbacks (setup_persistence_callbacks) and returns the chat.

Each call re-syncs in-memory state from the database.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/acts_as.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/acts_as_legacy.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/chat_methods.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/content.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/message_methods.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/model_methods.rb
